"""QLoRA-tune the Qwen2.5-1.5B model Stride calls through Ollama.

The base checkpoint is Qwen/Qwen2.5-1.5B-Instruct, the same weights as the
Ollama tag qwen2.5:1.5b. Training is 4-bit NF4 QLoRA and runs only on CUDA.
Loss is applied to the assistant JSON for intent, slot extraction, and the
grounded explanation. The prompts are the ones in app.graph.prompts.
"""

import sys
from pathlib import Path

import torch
from datasets import load_dataset
from peft import LoraConfig, TaskType, get_peft_model, prepare_model_for_kbit_training
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    DataCollatorWithPadding,
    Trainer,
    TrainingArguments,
)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

BASE_MODEL = "Qwen/Qwen2.5-1.5B-Instruct"
OUTPUT_DIR = Path(__file__).resolve().parent / "outputs" / "stride_qwen25_1_5b_qlora"
TRAIN_FILE = Path(__file__).resolve().parent / "data" / "train.jsonl"
VALID_FILE = Path(__file__).resolve().parent / "data" / "valid.jsonl"
TARGET_MODULES = ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]
MAX_LENGTH = 512


def main() -> None:
    if not torch.cuda.is_available():
        raise SystemExit(
            "QLoRA needs an NVIDIA GPU with CUDA and bitsandbytes. "
            "This machine cannot run 4-bit training."
        )
    if not TRAIN_FILE.exists() or not VALID_FILE.exists():
        from training.build_dataset import write_dataset

        write_dataset()

    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        quantization_config=BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
        ),
        device_map="auto",
    )
    model = prepare_model_for_kbit_training(model)
    model = get_peft_model(
        model,
        LoraConfig(
            r=8,
            lora_alpha=16,
            lora_dropout=0.05,
            bias="none",
            task_type=TaskType.CAUSAL_LM,
            target_modules=TARGET_MODULES,
        ),
    )

    dataset = load_dataset(
        "json",
        data_files={"train": str(TRAIN_FILE), "validation": str(VALID_FILE)},
    )

    def tokenize(batch: dict) -> dict:
        input_ids = []
        attention_mask = []
        labels = []
        for messages in batch["messages"]:
            prompt = tokenizer.apply_chat_template(
                messages[:-1], tokenize=False, add_generation_prompt=True
            )
            full = tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=False
            )
            prompt_ids = tokenizer(prompt, truncation=True, max_length=MAX_LENGTH)["input_ids"]
            encoded = tokenizer(full, truncation=True, max_length=MAX_LENGTH)
            masked = encoded["input_ids"].copy()
            cutoff = min(len(prompt_ids), len(masked))
            masked[:cutoff] = [-100] * cutoff
            input_ids.append(encoded["input_ids"])
            attention_mask.append(encoded["attention_mask"])
            labels.append(masked)
        return {"input_ids": input_ids, "attention_mask": attention_mask, "labels": labels}

    tokenized = dataset.map(tokenize, batched=True, remove_columns=dataset["train"].column_names)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    trainer = Trainer(
        model=model,
        args=TrainingArguments(
            output_dir=str(OUTPUT_DIR),
            num_train_epochs=1,
            per_device_train_batch_size=1,
            per_device_eval_batch_size=1,
            gradient_accumulation_steps=4,
            learning_rate=5e-5,
            logging_steps=10,
            eval_strategy="epoch",
            save_strategy="epoch",
            fp16=True,
            report_to=[],
            remove_unused_columns=False,
        ),
        train_dataset=tokenized["train"],
        eval_dataset=tokenized["validation"],
        data_collator=DataCollatorWithPadding(tokenizer=tokenizer, padding=True),
    )
    trainer.train()
    model.save_pretrained(OUTPUT_DIR)
    tokenizer.save_pretrained(OUTPUT_DIR)
    print(f"QLoRA adapter saved to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()

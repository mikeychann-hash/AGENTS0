from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List


@dataclass
class PeftConfig:
    model_name: str
    output_dir: str
    learning_rate: float = 2e-4
    num_train_epochs: int = 1
    batch_size: int = 4
    lora_rank: int = 8
    lora_alpha: int = 16
    lora_dropout: float = 0.05


def load_trajectories(path: Path) -> List[Dict[str, str]]:
    samples = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            obj = json.loads(line)
            prompt = obj["task"]["prompt"]
            answer = obj["result"]
            samples.append({"prompt": prompt, "answer": answer})
    return samples


def train_peft(config: PeftConfig, data_path: Path) -> None:
    try:
        from datasets import Dataset  # type: ignore
        from peft import LoraConfig, TaskType, get_peft_model  # type: ignore
        from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments, Trainer  # type: ignore
    except ImportError as exc:  # noqa: BLE001
        raise RuntimeError("Install transformers, datasets, peft, accelerate to run PEFT training") from exc

    samples = load_trajectories(data_path)
    dataset = Dataset.from_list(samples)
    tokenizer = AutoTokenizer.from_pretrained(config.model_name, use_fast=True)
    tokenizer.pad_token = tokenizer.eos_token

    def format_example(ex):
        text = f"Problem: {ex['prompt']}\nAnswer: {ex['answer']}"
        tokens = tokenizer(text, truncation=True, padding="max_length", max_length=512)
        tokens["labels"] = tokens["input_ids"].copy()
        return tokens

    tokenized = dataset.map(format_example, remove_columns=["prompt", "answer"])

    base_model = AutoModelForCausalLM.from_pretrained(config.model_name)
    lora_cfg = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=config.lora_rank,
        lora_alpha=config.lora_alpha,
        lora_dropout=config.lora_dropout,
        target_modules=["q_proj", "v_proj"],
    )
    model = get_peft_model(base_model, lora_cfg)

    args = TrainingArguments(
        output_dir=config.output_dir,
        per_device_train_batch_size=config.batch_size,
        num_train_epochs=config.num_train_epochs,
        learning_rate=config.learning_rate,
        logging_steps=10,
        save_steps=200,
        save_total_limit=2,
    )

    trainer = Trainer(model=model, args=args, train_dataset=tokenized, tokenizer=tokenizer)
    trainer.train()
    model.save_pretrained(config.output_dir)

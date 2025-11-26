import argparse
from pathlib import Path

import yaml

from agent0.logging.setup import configure_logging
from agent0.training.peft_trainer import PeftConfig, train_peft


def main() -> None:
    parser = argparse.ArgumentParser(description="Placeholder for PEFT/LoRA training pipeline.")
    parser.add_argument("--config", type=Path, default=Path("agent0/configs/3070ti.yaml"))
    parser.add_argument("--data", type=Path, required=True, help="Path to trajectories JSONL")
    parser.add_argument("--output", type=Path, default=Path("./peft-checkpoints"))
    parser.add_argument("--target", choices=["teacher", "student"], default="student")
    args = parser.parse_args()

    with args.config.open("r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    logger = configure_logging(Path(config["logging"]["base_dir"]))
    model_name = config["models"][args.target].get("base_model_name", config["models"][args.target].get("model", ""))
    peft_cfg = PeftConfig(
        model_name=model_name,
        output_dir=str(args.output),
    )
    logger.info("Starting PEFT training: target=%s model=%s data=%s", args.target, model_name, args.data)
    train_peft(peft_cfg, args.data)
    logger.info("Finished PEFT training; weights saved to %s", args.output)


if __name__ == "__main__":
    main()

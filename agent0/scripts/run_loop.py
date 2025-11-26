import argparse
import json
import logging
from pathlib import Path
from typing import Dict

import yaml

from agent0.loop.coordinator import Coordinator
from agent0.logging.local_mode_logger import configure_local_development_logging
from agent0.router.cloud_bridge import CloudRouter
from agent0.router.cli_bridge import call_cloud_cli


def main() -> None:
    parser = argparse.ArgumentParser(description="Run multiple Agent0 iterations.")
    parser.add_argument("--config", type=Path, default=Path("agent0/configs/3070ti.yaml"))
    parser.add_argument("--steps", type=int, default=5)
    parser.add_argument("--log-level", type=str, default="INFO")
    args = parser.parse_args()

    with args.config.open("r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    level = getattr(logging, args.log_level.upper(), logging.INFO)
    logger = configure_local_development_logging(Path(config["logging"]["base_dir"]), level=level)
    logger.info("Loaded config: %s", json.dumps(config, indent=2))

    coord = Coordinator(config)
    router = CloudRouter(
        local_threshold=config.get("router", {}).get("local_confidence_threshold", 0.4),
        escalate_threshold=config.get("router", {}).get("cloud_confidence_threshold", 0.7),
    )

    for i in range(args.steps):
        task_id = f"task-{i:04d}"
        student_signal: Dict[str, object] = {"next_task_id": task_id}
        traj = coord.run_once(student_signal)
        if not traj:
            logger.error("Step %s failed to produce a trajectory. Skipping to next.", task_id)
            continue
        fused = router.fuse_confidence(traj.reward.get("uncertainty", 0.0), traj.reward.get("total", 0.0))
        decision = router.decide(fused)
        cloud_resp = None
        if decision == "cloud":
            cloud_cmd = config.get("router", {}).get("cloud_command")
            if cloud_cmd:
                cloud_resp = call_cloud_cli(cloud_cmd, traj.task.prompt)
        logger.info(
            "Step %s: success=%s reward=%s route=%s cloud=%s",
            task_id,
            traj.success,
            traj.reward,
            decision,
            bool(cloud_resp),
        )


if __name__ == "__main__":
    main()

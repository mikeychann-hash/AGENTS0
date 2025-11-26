import argparse
import json
import logging
from pathlib import Path

import yaml

from agent0.loop.coordinator import Coordinator
from agent0.logging.setup import configure_logging
from agent0.router.cloud_bridge import CloudRouter
from agent0.router.cli_bridge import call_cloud_cli


def main() -> None:
    parser = argparse.ArgumentParser(description="Smoke test for Agent0 loop.")
    parser.add_argument("--config", type=Path, default=Path("agent0/configs/3070ti.yaml"))
    parser.add_argument("--log-level", type=str, default="INFO")
    args = parser.parse_args()

    with args.config.open("r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    level = getattr(logging, args.log_level.upper(), logging.INFO)
    logger = configure_logging(Path(config["logging"]["base_dir"]), level=level)
    logger.info("Loaded config: %s", json.dumps(config, indent=2))

    coord = Coordinator(config)
    router = CloudRouter(
        local_threshold=config.get("router", {}).get("local_confidence_threshold", 0.4),
        escalate_threshold=config.get("router", {}).get("cloud_confidence_threshold", 0.7),
    )
    cache_path = config.get("router", {}).get("cache_path", "./runs/router_cache.json")
    router.load_cache(cache_path)
    trajectory = coord.run_once({"next_task_id": "task-0001"})
    fused = router.fuse_confidence(trajectory.reward.get("uncertainty", 0.0), trajectory.reward.get("total", 0.0))
    decision = router.decide(fused)
    cloud_resp = None
    if decision == "cloud":
        cloud_cmd = config.get("router", {}).get("cloud_command")
        if cloud_cmd:
            cloud_resp = call_cloud_cli(cloud_cmd, trajectory.task.prompt)
    logger.info("Trajectory success=%s reward=%s route=%s cloud=%s", trajectory.success, trajectory.reward, decision, bool(cloud_resp))


if __name__ == "__main__":
    main()

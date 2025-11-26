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
    parser = argparse.ArgumentParser(description="Proxy that decides local vs cloud based on confidence.")
    parser.add_argument("--config", type=Path, default=Path("agent0/configs/3070ti.yaml"))
    parser.add_argument("--task", type=str, required=True, help="Task prompt to route")
    parser.add_argument("--domain", type=str, default="logic", help="Task domain (logic/code/math)")
    args = parser.parse_args()

    with args.config.open("r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    logger = configure_logging(Path(config["logging"]["base_dir"]), level=logging.INFO)
    coord = Coordinator(config)
    router = CloudRouter(
        local_threshold=config.get("router", {}).get("local_confidence_threshold", 0.4),
        escalate_threshold=config.get("router", {}).get("cloud_confidence_threshold", 0.7),
    )
    cache_path = config.get("router", {}).get("cache_path", "./runs/router_cache.json")
    router.load_cache(cache_path)

    cached = router.get_cache(args.task)
    if cached:
        logger.info("Cache hit. Returning cached result.")
        print(json.dumps(cached, indent=2))
        return

    traj = coord.run_once({"next_task_id": "manual-0001", "prompt_override": args.task, "domain_override": args.domain})
    decision = router.decide(traj.reward.get("uncertainty", 0.0) + 0.5)
    result = {"decision": decision, "result": traj.result, "reward": traj.reward}

    if decision == "cloud":
        cloud_cmd = config.get("router", {}).get("cloud_command")
        if cloud_cmd:
            cloud_resp = call_cloud_cli(cloud_cmd, args.task)
            result["cloud"] = cloud_resp

    router.set_cache(args.task, result)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

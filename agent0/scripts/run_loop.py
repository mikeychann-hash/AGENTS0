"""
Enhanced run_loop script with support for:
- Multi-domain curriculum
- Self-verification
- Frontier-based learning
"""

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


def print_banner():
    """Print startup banner with feature status"""
    banner = """
╔═══════════════════════════════════════════════════════════╗
║              Agent0 - Self-Evolving Agents                ║
║         Enhanced with Multi-Domain Curriculum             ║
╚═══════════════════════════════════════════════════════════╝
    """
    print(banner)


def print_config_summary(config: Dict):
    """Print summary of enabled features"""
    print("\n🔧 Configuration Summary:")
    print(f"  Teacher Model: {config['models']['teacher']['model']}")
    print(f"  Student Model: {config['models']['student']['model']}")
    
    # Curriculum settings
    curriculum = config.get("curriculum", {})
    print(f"\n📚 Curriculum:")
    print(f"  Frontier Mode: {'✅ Enabled' if curriculum.get('enable_frontier', True) else '❌ Disabled'}")
    print(f"  Target Success: {curriculum.get('target_success', 0.5):.0%}")
    print(f"  Domains: {', '.join(curriculum.get('domains', ['math']))}")
    
    # Verification settings
    verification = config.get("verification", {})
    if verification.get("enable", False):
        print(f"\n🔍 Self-Verification:")
        print(f"  Enabled: ✅")
        print(f"  Samples: {verification.get('num_samples', 3)}")
        print(f"  Threshold: {verification.get('confidence_threshold', 0.7):.0%}")
    else:
        print(f"\n🔍 Self-Verification: ❌ Disabled (set verification.enable=true to enable)")
    
    # Tools
    tooling = config.get("tooling", {})
    print(f"\n🛠️  Tools:")
    print(f"  Python: {'✅' if tooling.get('enable_python') else '❌'}")
    print(f"  Math: {'✅' if tooling.get('enable_math') else '❌'}")
    print(f"  Shell: {'✅' if tooling.get('enable_shell') else '❌'}")
    
    print(f"\n⚠️  LOCAL MODE: Code executes directly on your machine (no sandboxing)")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run multiple Agent0 iterations with enhanced curriculum.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run 10 iterations with default config
  python -m agent0.scripts.run_loop --steps 10
  
  # Enable self-verification
  python -m agent0.scripts.run_loop --steps 5 --verify
  
  # Disable frontier mode (use round-robin domains)
  python -m agent0.scripts.run_loop --steps 10 --no-frontier
  
  # Run with specific domains only
  python -m agent0.scripts.run_loop --steps 10 --domains math logic
        """
    )
    parser.add_argument("--config", type=Path, default=Path("agent0/configs/3070ti.yaml"),
                       help="Path to config YAML file")
    parser.add_argument("--steps", type=int, default=5,
                       help="Number of iterations to run")
    parser.add_argument("--log-level", type=str, default="INFO",
                       choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                       help="Logging level")
    parser.add_argument("--verify", action="store_true",
                       help="Enable self-verification (overrides config)")
    parser.add_argument("--no-frontier", action="store_true",
                       help="Disable frontier-based curriculum (use round-robin)")
    parser.add_argument("--domains", nargs="+", choices=["math", "logic", "code"],
                       help="Domains to train on (overrides config)")
    args = parser.parse_args()

    # Load config
    with args.config.open("r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # Apply CLI overrides
    if args.verify:
        config.setdefault("verification", {})["enable"] = True
    
    if args.no_frontier:
        config.setdefault("curriculum", {})["enable_frontier"] = False
    
    if args.domains:
        config.setdefault("curriculum", {})["domains"] = args.domains

    # Setup logging
    level = getattr(logging, args.log_level.upper(), logging.INFO)
    logger = configure_local_development_logging(Path(config["logging"]["base_dir"]), level=level)
    
    # Print banner and config
    print_banner()
    print_config_summary(config)
    
    logger.info("Loaded config: %s", json.dumps(config, indent=2))

    # Create coordinator
    coord = Coordinator(config)
    
    # Router (for cloud escalation)
    router = CloudRouter(
        local_threshold=config.get("router", {}).get("local_confidence_threshold", 0.4),
        escalate_threshold=config.get("router", {}).get("cloud_confidence_threshold", 0.7),
    )

    # Run evolution loop
    print(f"\n🚀 Starting {args.steps} iteration(s)...\n")
    
    successes = 0
    total_reward = 0.0
    domain_stats = {}
    
    for i in range(args.steps):
        task_id = f"task-{i:04d}"
        student_signal: Dict[str, object] = {"next_task_id": task_id}
        
        print(f"{'='*60}")
        print(f"Iteration {i+1}/{args.steps} - {task_id}")
        print(f"{'='*60}")
        
        traj = coord.run_once(student_signal)
        
        if not traj:
            logger.error("Step %s failed to produce a trajectory. Skipping to next.", task_id)
            continue
        
        # Track stats
        if traj.success:
            successes += 1
        total_reward += traj.reward.get("total", 0.0)
        
        domain = traj.task.domain
        if domain not in domain_stats:
            domain_stats[domain] = {"total": 0, "success": 0}
        domain_stats[domain]["total"] += 1
        if traj.success:
            domain_stats[domain]["success"] += 1
        
        # Router decision
        fused = router.fuse_confidence(
            traj.reward.get("uncertainty", 0.0),
            traj.reward.get("total", 0.0)
        )
        decision = router.decide(fused)
        
        # Cloud escalation
        cloud_resp = None
        if decision == "cloud":
            cloud_cmd = config.get("router", {}).get("cloud_command")
            if cloud_cmd:
                cloud_resp = call_cloud_cli(cloud_cmd, traj.task.prompt)
        
        # Print iteration summary
        print(f"\n📊 Iteration Summary:")
        print(f"  Domain: {domain}")
        print(f"  Success: {'✅' if traj.success else '❌'}")
        print(f"  Reward: {traj.reward.get('total', 0.0):.3f}")
        if "verification_confidence" in traj.metrics:
            print(f"  Verification: {traj.metrics['verification_confidence']:.1%}")
        print(f"  Route: {decision}")
        if cloud_resp:
            print(f"  Cloud: ✅ Used")
        print()
    
    # Final summary
    print(f"\n{'='*60}")
    print(f"🎯 Final Summary ({args.steps} iterations)")
    print(f"{'='*60}")
    print(f"Overall Success Rate: {successes}/{args.steps} ({successes/args.steps:.1%})")
    print(f"Average Reward: {total_reward/args.steps:.3f}")
    print(f"\nPer-Domain Performance:")
    for domain, stats in domain_stats.items():
        sr = stats["success"] / stats["total"] if stats["total"] > 0 else 0
        print(f"  {domain.capitalize()}: {stats['success']}/{stats['total']} ({sr:.1%})")
    print(f"\n✅ Run complete! Trajectories saved to: {config['logging']['base_dir']}/trajectories.jsonl")
    print()


if __name__ == "__main__":
    main()

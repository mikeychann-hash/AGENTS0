"""
Quick test script to verify enhanced features work correctly.
"""

import sys
from pathlib import Path

def test_imports():
    """Test that all enhanced modules can be imported"""
    print("Testing imports...")
    
    try:
        from agent0.loop.curriculum_scheduler import CurriculumScheduler, DomainState
        print("  ✅ Enhanced curriculum scheduler")
    except Exception as e:
        print(f"  ❌ Curriculum scheduler: {e}")
        return False
    
    try:
        from agent0.agents.teacher import TeacherAgent
        print("  ✅ Multi-domain teacher")
    except Exception as e:
        print(f"  ❌ Teacher agent: {e}")
        return False
    
    try:
        from agent0.tools.tool_composer import ToolComposer, ToolStep
        print("  ✅ Tool composer")
    except Exception as e:
        print(f"  ❌ Tool composer: {e}")
        return False
    
    try:
        from agent0.agents.self_verifier import SelfVerifier, VerificationResult
        print("  ✅ Self-verifier")
    except Exception as e:
        print(f"  ❌ Self-verifier: {e}")
        return False
    
    try:
        from agent0.loop.coordinator import Coordinator
        print("  ✅ Enhanced coordinator")
    except Exception as e:
        print(f"  ❌ Coordinator: {e}")
        return False
    
    return True


def test_curriculum_scheduler():
    """Test curriculum scheduler functionality"""
    print("\nTesting curriculum scheduler...")
    
    from agent0.loop.curriculum_scheduler import CurriculumScheduler
    
    try:
        # Create scheduler
        sched = CurriculumScheduler(
            target_success=0.5,
            frontier_window=0.1,
            enable_frontier=True
        )
        
        # Run updates
        for i in range(10):
            sched.update(success=(i % 2 == 0), domain="math")
        
        # Get signal
        signal = sched.next_signal()
        
        assert "domain_override" in signal
        assert "difficulty" in signal
        assert "frontier_mode" in signal
        
        # Get status
        status = sched.get_status()
        assert "domains" in status
        assert "step" in status
        
        print("  ✅ Curriculum scheduler works correctly")
        return True
        
    except Exception as e:
        print(f"  ❌ Curriculum scheduler test failed: {e}")
        return False


def test_teacher_domains():
    """Test multi-domain task generation"""
    print("\nTesting multi-domain teacher...")
    
    from agent0.agents.teacher import TeacherAgent
    
    try:
        # Mock config
        config = {
            "backend": "ollama",
            "model": "qwen2.5:3b",
            "temperature": 0.7
        }
        
        teacher = TeacherAgent(config)
        
        # Test each domain
        for domain in ["math", "logic", "code"]:
            task = teacher.generate_task({
                "domain_override": domain,
                "difficulty": 0.5,
                "next_task_id": f"test-{domain}"
            })
            
            assert task.domain == domain
            assert task.prompt is not None
            print(f"  ✅ {domain.capitalize()} task: {task.prompt[:60]}...")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Teacher test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_tool_composer():
    """Test tool composition framework"""
    print("\nTesting tool composer...")
    
    from agent0.tools.tool_composer import ToolComposer, ToolStep
    
    try:
        # Mock tools
        def mock_tool_a(input_str):
            return {"status": "ok", "result": "42"}
        
        def mock_tool_b(input_str):
            return {"status": "ok", "result": f"processed: {input_str}"}
        
        composer = ToolComposer({
            "tool_a": mock_tool_a,
            "tool_b": mock_tool_b
        })
        
        # Create plan
        plan = [
            ToolStep(step_id="step_1", tool="tool_a", input="test"),
            ToolStep(
                step_id="step_2",
                tool="tool_b",
                input="{{step_1.result}}",
                depends_on=["step_1"]
            )
        ]
        
        # Execute
        results = composer.execute_plan(plan)
        
        assert "step_1" in results
        assert "step_2" in results
        assert results["step_1"]["status"] == "ok"
        
        print("  ✅ Tool composer works correctly")
        return True
        
    except Exception as e:
        print(f"  ❌ Tool composer test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_config_parsing():
    """Test that enhanced config can be loaded"""
    print("\nTesting config parsing...")
    
    import yaml
    
    try:
        config_path = Path("agent0/configs/3070ti.yaml")
        
        if not config_path.exists():
            print(f"  ⚠️  Config not found: {config_path}")
            return False
        
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        
        # Check for new sections
        assert "curriculum" in config, "Missing curriculum section"
        assert "verification" in config, "Missing verification section"
        
        curriculum = config["curriculum"]
        assert "enable_frontier" in curriculum
        assert "domains" in curriculum
        
        verification = config["verification"]
        assert "enable" in verification
        assert "num_samples" in verification
        
        print("  ✅ Config has all required sections")
        return True
        
    except Exception as e:
        print(f"  ❌ Config test failed: {e}")
        return False


def main():
    """Run all tests"""
    print("="*60)
    print("Agent0 Enhancement Test Suite")
    print("="*60)
    
    tests = [
        test_imports,
        test_curriculum_scheduler,
        test_teacher_domains,
        test_tool_composer,
        test_config_parsing
    ]
    
    passed = 0
    failed = 0
    
    for test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"  ❌ Test crashed: {e}")
            failed += 1
    
    print("\n" + "="*60)
    print(f"Results: {passed} passed, {failed} failed")
    print("="*60)
    
    if failed == 0:
        print("\n✅ All tests passed! Enhanced features are ready to use.")
        return 0
    else:
        print(f"\n❌ {failed} test(s) failed. Please fix before using.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

from webyx_env.server.webyx_env_environment import WebyxEnvironment
from webyx_env.models import WebyxAction

env = WebyxEnvironment()

FIXES = {
    "easy": [
        ("#hero",          "fix", 'alt="Hero image"'),
        ("#team",          "fix", 'alt="Team photo"'),
        ("#office",        "fix", 'alt="Office space"'),
        ("#award",         "fix", 'alt="Award ceremony"'),
    ],
    "medium": [
        ("#full-name",  "fix", '<label for="full-name">Full name</label>'),
        ("#email",      "fix", '<label for="email">Email address</label>'),
        ("#submit-btn", "fix", 'aria-label="Submit form"'),
        ("#lead",       "fix", 'class="muted high-contrast"'),
    ],
    "hard": [
        ("#nav-links",      "fix", '<nav id="nav-links"><a id="home-link" href="/home">Home</a><a id="pricing-link" href="/pricing">Pricing</a></nav>'),
        ("#feature-shot",   "fix", 'alt="Feature screenshot"'),
        ("#page-root",      "fix", 'lang="en"'),
        ("#shipping-name",  "fix", '<label for="shipping-name">Shipping name</label>'),
        ("#shipping-email", "fix", 'autocomplete="email"'),
        ("#fine-print",     "fix", 'class="muted high-contrast"'),
        ("#fine-print",     "fix", 'class="muted high-contrast"'),
        ("#promo-banner",   "fix", 'role="region"'),
    ],
}

for task_id, actions in FIXES.items():
    obs = env.reset(task_id=task_id)
    print(f"\n{'='*40}")
    print(f"task: {task_id} | violations: {len(obs.violations)} | max_steps: {obs.max_steps}")
    print(f"{'='*40}")

    rewards = []
    for target, action_type, proposed_fix in actions:
        action = WebyxAction(action_type=action_type, target=target, proposed_fix=proposed_fix)
        obs = env.step(action)
        rewards.append(obs.reward)
        print(f"  {action_type} {target:<25} reward={obs.reward:+.2f}  score={obs.episode_score:.4f}  done={obs.done}")

    print(f"\n  total rewards: {rewards}")
    print(f"  final score:   {obs.episode_score:.4f}")
    print(f"  success:       {obs.episode_score >= 0.5}")
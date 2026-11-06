"""ServiceNow platform release hierarchy and capability evaluation."""

from now_workbench.releases.models import (
    RELEASE_FAMILIES,
    ReleaseCompatibilityResult,
)

# Known platform innovations mapped to the minimum release where they were introduced
FEATURE_MINIMUM_RELEASES: dict[str, tuple[str, str]] = {
    "AI Agent Studio": (
        "Xanadu",
        "Autonomous AI agent orchestration and studio introduced in Xanadu.",
    ),
    "Now Assist GenAI": (
        "Vancouver",
        "Now Assist Generative AI summarization and skill controller launched in Vancouver.",
    ),
    "Prompt Controller": (
        "Washington DC",
        "Dynamic prompt builder and prompt controller introduced in Washington DC.",
    ),
    "Fluent SDK": (
        "Washington DC",
        "ServiceNow Fluent TypeScript SDK (@servicenow/sdk) requires Washington DC or later.",
    ),
    "Service Operations Workspace": (
        "San Diego",
        "Service Operations Workspace (SOW) replaced legacy Agent Workspace in San Diego.",
    ),
    "Next Experience UI": (
        "San Diego",
        "Next Experience Polaris navigation framework was introduced in San Diego.",
    ),
}


def normalize_release(name: str) -> str:
    """Normalize ServiceNow family release name for uniform matching."""
    cleaned = name.strip()
    norm = cleaned.lower().replace("-", " ").replace("_", " ")
    compact = norm.replace(" ", "")
    for family in RELEASE_FAMILIES:
        # Compact match covers build-string tokens such as "washingtondc" and "sandiego".
        if compact == family.lower().replace(" ", "") or (
            family == "Washington DC" and norm in ("washington", "wdc")
        ):
            return family
    # Fallback to Title Case if unknown
    return cleaned.title()


def get_release_index(name: str) -> int:
    """Return index of the release family in chronological order, or -1 if unknown."""
    norm = normalize_release(name)
    try:
        return RELEASE_FAMILIES.index(norm)
    except ValueError:
        return -1


def compare_releases(release_a: str, release_b: str) -> int:
    """Compare two releases chronologically.

    Returns:
        -1 if release_a < release_b
         0 if release_a == release_b
         1 if release_a > release_b
    """
    idx_a = get_release_index(release_a)
    idx_b = get_release_index(release_b)

    if idx_a == -1 or idx_b == -1:
        # Fallback to lexical comparison if unknown
        norm_a = normalize_release(release_a)
        norm_b = normalize_release(release_b)
        if norm_a < norm_b:
            return -1
        if norm_a > norm_b:
            return 1
        return 0

    if idx_a < idx_b:
        return -1
    if idx_a > idx_b:
        return 1
    return 0


def is_release_compatible(instance_release: str, min_release: str) -> bool:
    """Return True if instance_release meets or exceeds min_release."""
    return compare_releases(instance_release, min_release) >= 0


def check_feature_compatibility(feature: str, instance_release: str) -> tuple[bool, str]:
    """Check if a specific platform capability is supported on the target release."""
    for feat_name, (min_rel, reason) in FEATURE_MINIMUM_RELEASES.items():
        if feat_name.lower() in feature.lower():
            if not is_release_compatible(instance_release, min_rel):
                return False, f"Feature '{feat_name}' requires minimum release {min_rel}. {reason}"
            return True, f"Feature '{feat_name}' supported (requires {min_rel}+)."
    return True, f"Feature '{feature}' has no specific release constraint."


def evaluate_release_prerequisites(
    instance_release: str,
    min_release: str,
    tags: list[str] | None = None,
) -> ReleaseCompatibilityResult:
    """Evaluate whether an instance satisfies a bundle's minimum release and capabilities."""
    norm_inst = normalize_release(instance_release)
    norm_min = normalize_release(min_release)

    is_compat = is_release_compatible(norm_inst, norm_min)
    unsupported: list[str] = []
    required: list[str] = []

    # Check tags for known features
    if tags:
        for tag in tags:
            for feat_name, (feat_min, _) in FEATURE_MINIMUM_RELEASES.items():
                if feat_name.lower() in tag.lower():
                    required.append(feat_name)
                    if not is_release_compatible(norm_inst, feat_min):
                        unsupported.append(feat_name)

    if not is_compat:
        reason = (
            f"Instance release '{norm_inst}' is below the required minimum release '{norm_min}'. "
            f"Cannot run demonstrations designed for {norm_min} on {norm_inst}."
        )
    elif unsupported:
        feats = ", ".join(unsupported)
        reason = (
            f"Instance release '{norm_inst}' is missing capabilities for: {feats}. "
            f"Minimum release required for those features is {norm_min}."
        )
        is_compat = False
    else:
        reason = (
            f"Release verified: '{norm_inst}' satisfies minimum platform requirement '{norm_min}'."
        )

    return ReleaseCompatibilityResult(
        is_compatible=is_compat,
        instance_release=norm_inst,
        min_release=norm_min,
        reason=reason,
        required_features=sorted(set(required)),
        unsupported_features=sorted(set(unsupported)),
    )

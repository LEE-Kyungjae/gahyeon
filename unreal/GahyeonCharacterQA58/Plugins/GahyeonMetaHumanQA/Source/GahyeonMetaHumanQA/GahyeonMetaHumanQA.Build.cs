using UnrealBuildTool;

public class GahyeonMetaHumanQA : ModuleRules
{
    public GahyeonMetaHumanQA(ReadOnlyTargetRules Target) : base(Target)
    {
        PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
        PublicDependencyModuleNames.AddRange(new[] { "Core", "CoreUObject", "Engine" });
        PrivateDependencyModuleNames.AddRange(new[]
        {
            "UnrealEd",
            "Slate",
            "MetaHumanCore",
            "MetaHumanIdentity",
            "MetaHumanIdentityEditor",
            "MetaHumanCharacter",
            "MetaHumanCharacterEditor",
            "MetaHumanToolkit"
        });
        PrivateIncludePaths.Add(
            System.IO.Path.Combine(
                EngineDirectory,
                "Plugins/MetaHuman/MetaHumanAnimator/Source/MetaHumanIdentityEditor/Private"
            )
        );
    }
}

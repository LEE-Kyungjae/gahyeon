using UnrealBuildTool;

public class GahyeonDesktopMetaHumanPOC : ModuleRules
{
    public GahyeonDesktopMetaHumanPOC(ReadOnlyTargetRules Target) : base(Target)
    {
        PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
        PublicDependencyModuleNames.AddRange(new[] { "Core", "CoreUObject", "Engine" });
        PrivateDependencyModuleNames.AddRange(new[]
        {
            "AudioCapture",
            "CinematicCamera",
            "MovieSceneCapture",
            "Slate",
            "SlateCore",
            "RHI"
        });
        if (Target.Platform == UnrealTargetPlatform.Mac)
        {
            PublicFrameworks.AddRange(new[] { "Metal", "IOSurface" });
        }
    }
}

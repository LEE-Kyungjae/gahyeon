using UnrealBuildTool;

public class GahyeonRuntimeCore : ModuleRules
{
    public GahyeonRuntimeCore(ReadOnlyTargetRules Target) : base(Target)
    {
        PCHUsage = PCHUsageMode.NoPCHs;
        CppStandard = CppStandardVersion.Cpp20;
        bUseUnity = false;
        bEnableExceptions = true;

        ForceIncludeFiles.Add("HAL/Platform.h");

        PublicDependencyModuleNames.Add("Core");
        PublicDefinitions.Add("GAHYEON_RUNTIME_CORE_API=GAHYEONRUNTIMECORE_API");
    }
}

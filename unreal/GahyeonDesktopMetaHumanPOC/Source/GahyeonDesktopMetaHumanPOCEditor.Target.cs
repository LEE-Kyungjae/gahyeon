using UnrealBuildTool;

public class GahyeonDesktopMetaHumanPOCEditorTarget : TargetRules
{
    public GahyeonDesktopMetaHumanPOCEditorTarget(TargetInfo Target) : base(Target)
    {
        Type = TargetType.Editor;
        DefaultBuildSettings = BuildSettingsVersion.V7;
        IncludeOrderVersion = EngineIncludeOrderVersion.Unreal5_8;
        ExtraModuleNames.Add("GahyeonDesktopMetaHumanPOC");
    }
}

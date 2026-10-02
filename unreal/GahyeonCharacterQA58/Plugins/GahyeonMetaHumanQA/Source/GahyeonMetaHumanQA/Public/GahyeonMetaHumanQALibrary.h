#pragma once

#include "Kismet/BlueprintFunctionLibrary.h"
#include "GahyeonMetaHumanQALibrary.generated.h"

class USkeletalMeshComponent;

UCLASS()
class GAHYEONMETAHUMANQA_API UGahyeonMetaHumanQALibrary : public UBlueprintFunctionLibrary
{
    GENERATED_BODY()

public:
    UFUNCTION(BlueprintCallable, Category = "Gahyeon|MetaHuman QA")
    static bool TrackAndConformIdentity(const FString& IdentityAssetPath, FString& OutMessage);

    UFUNCTION(BlueprintCallable, Category = "Gahyeon|MetaHuman QA")
    static bool ConformCharacterFromIdentity(
        UObject* Character,
        UObject* Identity,
        bool bUseEyeMeshes,
        bool bUseTeethMesh,
        FString& OutMessage);

    UFUNCTION(BlueprintCallable, Category = "Gahyeon|MetaHuman QA")
    static bool ForceRefreshSkeletalMorphs(
        USkeletalMeshComponent* Component,
        FString& OutMessage);
};

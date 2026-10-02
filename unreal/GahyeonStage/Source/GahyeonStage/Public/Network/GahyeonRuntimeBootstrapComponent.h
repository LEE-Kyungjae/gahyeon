#pragma once

#include "Components/ActorComponent.h"
#include "GahyeonRuntimeBootstrapComponent.generated.h"

/**
 * Opt-in command-line bootstrap for standalone/Desktop runtime launches.
 *
 * It stays inert unless -GahyeonAutoConnect is present. The bearer token is
 * intentionally read only from GAHYEON_CLIENT_TOKEN so it never appears in a
 * process command line or captured launch evidence.
 */
UCLASS(ClassGroup = (Gahyeon))
class GAHYEONSTAGE_API UGahyeonRuntimeBootstrapComponent final : public UActorComponent
{
    GENERATED_BODY()

public:
    UGahyeonRuntimeBootstrapComponent();

    virtual void BeginPlay() override;
};

#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

python3 scripts/test_verify_ai_quality_catalog.py
python3 scripts/verify_ai_quality_catalog.py
python3 -m unittest scripts.test_macos_core_tunnel scripts.test_desktop_service_smoke scripts.test_macos_chat_timeout scripts.test_macos_production_core scripts.test_lme_chat_answer scripts.test_macos_segmented_speech scripts.test_agent_latency_summary scripts.test_macos_speech_cancellation
python3 scripts/test_create_autonomy_contract.py
python3 scripts/test_decide_autonomy_action.py
python3 scripts/test_evaluate_canary_observation.py
python3 scripts/test_verify_blind_tts_review.py
python3 scripts/test_piper_listening_review.py
python3 scripts/test_piper_runtime_server.py
python3 scripts/test_piper_pronunciation.py
python3 scripts/test_qwen_original_voice_contract.py
./gradlew test \
  --tests 'com.gahyeonbot.adapters.discord.voice.VoiceAssistantTranscriptionGuardTest' \
  --tests 'com.gahyeonbot.services.ai.agent.AgentLatencyDiagnosticsTest' \
  --tests 'com.gahyeonbot.services.assistant.OpenAiTranscriptionSilenceTest' \
  --tests 'com.gahyeonbot.services.ai.agent.AgentResponseSanitizerTest' \
  --tests 'com.gahyeonbot.services.ai.agent.DefaultAgentRuntimeCancellationTest' \
  --tests 'com.gahyeonbot.services.ai.agent.SensitiveDataRedactorTest' \
  --tests 'com.gahyeonbot.services.ai.agent.AgentApprovalAuditRedactionTest' \
  --tests 'com.gahyeonbot.services.ai.agent.RecoverableToolOutputCompressorTest' \
  --tests 'com.gahyeonbot.services.ai.agent.EphemeralToolOutputArchiveTest' \
  --tests 'com.gahyeonbot.services.ai.agent.work.ResearchSkillSelectionRecoveryTest' \
  --tests 'com.gahyeonbot.services.ai.agent.work.ResearchCitationRecoveryTest' \
  --tests 'com.gahyeonbot.services.ai.agent.work.CopperResearchRoutingTest' \
  --tests 'com.gahyeonbot.services.ai.agent.skills.AgentSkillHarnessFactoryTest' \
  --tests 'com.gahyeonbot.services.ai.agent.skills.AgentSkillHarnessTest' \
  --tests 'com.gahyeonbot.services.ai.agent.work.CopperSourceDiscoveryTest' \
  --tests 'com.gahyeonbot.services.ai.agent.MarketFailureMessageTest' \
  --tests 'com.gahyeonbot.services.ai.agent.CopperDailyLookupEvidenceTest' \
  --tests 'com.gahyeonbot.services.ai.agent.work.ResearchUnavailableSourceTest' \
  --tests 'com.gahyeonbot.services.ai.agent.work.DesktopResearchAvailabilityTest' \
  --tests 'com.gahyeonbot.services.ai.agent.work.TrustedResearchWorkTest' \
  --tests 'com.gahyeonbot.services.ai.WeatherToolsTest'

echo "Gahyeon AI quality gate passed."

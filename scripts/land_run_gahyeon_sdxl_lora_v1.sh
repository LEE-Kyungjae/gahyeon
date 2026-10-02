#!/usr/bin/env bash
set -euo pipefail

steps="${1:-800}"
root=/opt/zaeze-ai/training/gahyeon-sdxl-v1
trainer=/opt/zaeze-ai/sd-scripts
python_env=/opt/zaeze-ai/sdxl-lora-venv

cd "$trainer"
exec "$python_env/bin/accelerate" launch \
  --num_processes 1 \
  --num_cpu_threads_per_process 1 \
  sdxl_train_network.py \
  --pretrained_model_name_or_path /opt/zaeze-ai/comfyui/models/checkpoints/sd_xl_base_1.0.safetensors \
  --train_data_dir "$root/dataset/train" \
  --output_dir "$root/outputs" \
  --output_name gahyeon-sdxl-v1 \
  --logging_dir "$root/logs/full" \
  --caption_extension .txt \
  --resolution 512,512 \
  --enable_bucket \
  --min_bucket_reso 384 \
  --max_bucket_reso 640 \
  --bucket_reso_steps 64 \
  --train_batch_size 1 \
  --max_train_steps "$steps" \
  --network_module networks.lora \
  --network_dim 4 \
  --network_alpha 4 \
  --network_train_unet_only \
  --learning_rate 1e-4 \
  --optimizer_type Adafactor \
  --optimizer_args relative_step=False scale_parameter=False warmup_init=False \
  --lr_scheduler constant_with_warmup \
  --lr_warmup_steps 40 \
  --mixed_precision fp16 \
  --save_precision fp16 \
  --max_grad_norm 0 \
  --gradient_checkpointing \
  --cache_latents \
  --cache_latents_to_disk \
  --cache_text_encoder_outputs \
  --cache_text_encoder_outputs_to_disk \
  --sdpa \
  --no_half_vae \
  --vae_batch_size 1 \
  --max_data_loader_n_workers 0 \
  --seed 4242 \
  --save_model_as safetensors \
  --save_every_n_steps 200 \
  --save_last_n_steps 800 \
  --save_state \
  --save_last_n_steps_state 400 \
  --save_state_on_train_end

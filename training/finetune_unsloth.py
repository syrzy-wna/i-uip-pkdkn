"""Templat Skrip Fine-Tuning QLoRA Model Gemma Tempatan Menggunakan Unsloth.

Skrip ini direka sebagai templat sedia guna apabila anda ingin melatih
(`fine-tune`) model tempatan `gemma-3-12b-it` menggunakan arkib Kertas Siasatan
yang telah disamarkan oleh `prepare_dataset.py`, dan mengeksportnya terus ke
format GGUF untuk dijalankan melalui Ollama (`uip-gemma3:12b`).

Prasyarat persekitaran GPU latihan (contoh: RTX 4090 / A100 / Colab):
    pip install unsloth datasets trl transformers accelerate bitsandbytes
"""

from __future__ import annotations

import argparse
from pathlib import Path


MODELFILE_TEMPLATE = """FROM ./uip-gemma3-12b-q4_k_m.gguf
PARAMETER temperature 0.1
PARAMETER top_p 0.9
PARAMETER num_ctx 8192
SYSTEM \"\"\"Anda ialah pakar perundangan dan pendakwaan kesihatan awam Unit Perundangan dan Pendakwaan (UIP), Kementerian Kesihatan Malaysia. Anda mahir dalam laras bahasa rasmi Borang 114, Diari Siasatan, Fakta Kes, serta penyamaran data sulit OSA/PDPA.\"\"\"
"""


def run_finetune(
    dataset_path: Path,
    output_dir: Path,
    base_model: str = "unsloth/gemma-3-12b-it-bnb-4bit",
    max_seq_length: int = 4096,
    max_steps: int = 120,
    learning_rate: float = 2e-4,
) -> None:
    try:
        from datasets import load_dataset
        from trl import SFTConfig, SFTTrainer
        from unsloth import FastLanguageModel
    except ImportError as exc:
        raise SystemExit(
            "[AMARAN] Pakej latihan GPU (unsloth / trl / datasets) belum dipasang dalam persekitaran ini.\n"
            "Jalankan skrip ini pada mesin ber-GPU CUDA selepas memasang:\n"
            "  pip install unsloth datasets trl transformers accelerate bitsandbytes\n"
            f"Ralat asal: {exc}"
        ) from exc

    if not dataset_path.exists():
        raise FileNotFoundError(
            f"Fail dataset tidak dijumpai: {dataset_path}. Jalankan `prepare_dataset.py` terlebih dahulu."
        )

    print(f"[1/5] Memuatkan model asas 4-bit: {base_model}")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=base_model,
        max_seq_length=max_seq_length,
        dtype=None,
        load_in_4bit=True,
    )

    print("[2/5] Memasang penyesuai LoRA (QLoRA r=16, alpha=32)")
    model = FastLanguageModel.get_peft_model(
        model,
        r=16,
        target_modules=[
            "q_proj",
            "k_proj",
            "v_proj",
            "o_proj",
            "gate_proj",
            "up_proj",
            "down_proj",
        ],
        lora_alpha=32,
        lora_dropout=0,
        bias="none",
        use_gradient_checkpointing="unsloth",
        random_state=3407,
    )

    print(f"[3/5] Memuatkan dataset JSONL: {dataset_path}")
    dataset = load_dataset("json", data_files=str(dataset_path), split="train")

    def format_conversations(batch):
        texts = []
        for conv in batch["conversations"]:
            messages = []
            for turn in conv:
                role = "user" if turn["from"] == "human" else (
                    "assistant" if turn["from"] == "gpt" else "system"
                )
                messages.append({"role": role, "content": turn["value"]})
            texts.append(
                tokenizer.apply_chat_template(
                    messages, tokenize=False, add_generation_prompt=False
                )
            )
        return {"text": texts}

    dataset = dataset.map(format_conversations, batched=True)

    output_dir.mkdir(parents=True, exist_ok=True)
    print("[4/5] Memulakan latihan SFTTrainer...")
    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=dataset,
        args=SFTConfig(
            dataset_text_field="text",
            max_seq_length=max_seq_length,
            per_device_train_batch_size=2,
            gradient_accumulation_steps=4,
            warmup_steps=10,
            max_steps=max_steps,
            learning_rate=learning_rate,
            logging_steps=5,
            output_dir=str(output_dir / "checkpoints"),
            optim="adamw_8bit",
            seed=3407,
        ),
    )
    trainer.train()

    print("[5/5] Mengeksport ke GGUF (Q4_K_M) dan Modelfile Ollama...")
    gguf_dir = output_dir / "ollama_export"
    gguf_dir.mkdir(parents=True, exist_ok=True)
    model.save_pretrained_gguf(
        str(gguf_dir),
        tokenizer,
        quantization_method="q4_k_m",
    )
    (gguf_dir / "Modelfile").write_text(MODELFILE_TEMPLATE, encoding="utf-8")
    print(
        "\n[SELESAI] Untuk mendaftarkan model tersuai ke Ollama, jalankan:\n"
        f"  cd {gguf_dir}\n"
        "  ollama create uip-gemma3:12b -f Modelfile\n"
        "Kemudian kemas kini OLLAMA_MODEL=uip-gemma3:12b dalam fail .env anda."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Fine-tune Gemma-3-12B untuk laras bahasa UIP.")
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path(__file__).resolve().parent / "uip_dataset.jsonl",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parent / "outputs",
    )
    parser.add_argument("--base-model", type=str, default="unsloth/gemma-3-12b-it-bnb-4bit")
    parser.add_argument("--max-steps", type=int, default=120)
    args = parser.parse_args()

    run_finetune(
        dataset_path=args.dataset,
        output_dir=args.output_dir,
        base_model=args.base_model,
        max_steps=args.max_steps,
    )


if __name__ == "__main__":
    main()

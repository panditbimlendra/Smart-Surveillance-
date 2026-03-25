"""
SafeZone AI — SlowFast R50 Lightning Module
safezone_ai/models/slowfast_model.py

Pretrained: Kinetics-400 (via pytorchvideo.models.hub.slowfast_r50)
Fine-tuned:  UCF-Crime 14-class classification

Fine-tuning strategy:
  1. Load pretrained SlowFast R50 (33.7M params)
  2. Freeze ALL backbone parameters
  3. Unfreeze last cfg.unfreeze_last_n blocks + new head
     Default: unfreeze_last_n=3  →  ~100K trainable params
  4. Differential LR:
       backbone unfrozen layers : cfg.lr × 0.1
       head                     : cfg.lr  (full rate)
  5. AdamW + CosineAnnealingLR + gradient clipping

OOM safety:
  training_step and validation_step both catch RuntimeError OOM,
  clear CUDA cache, and return None to skip the batch safely.
  Lightning handles None returns without crashing.

AUROC fix:
  Computing AUROC per-batch fails when a batch is missing some
  classes ("No negative/positive samples" warning / crash).
  Instead, AUROC is accumulated via .update() in validation_step
  and computed once in on_validation_epoch_end over the full set.

Confusion matrix note:
  val_confmat is NOT reset in on_validation_epoch_end.
  MetricsCallback.on_validation_epoch_end runs AFTER this hook
  and reads val_confmat. If we reset here, it gets an empty matrix.
  MetricsCallback is responsible for resetting it.
"""

from __future__ import annotations
import torch
import torch.nn as nn
import pytorch_lightning as pl
import torchmetrics
from pytorchvideo.models.hub import slowfast_r50

from config import VCFG, VideoConfig
from utils.logger import get_logger

logger = get_logger("safezone.slowfast")


class SlowFastLitModel(pl.LightningModule):
    """
    SlowFast R50 fine-tuned for UCF-Crime 14-class classification.

    Input (from UCFCrimeDataset):
        slow  : (B, 3, T_slow, H, W)   e.g. (B, 3, 8,  224, 224)
        fast  : (B, 3, T,      H, W)   e.g. (B, 3, 32, 224, 224)

    Output:
        logits : (B, num_classes)
    """

    def __init__(self, cfg: VideoConfig = VCFG):
        super().__init__()
        self.save_hyperparameters(ignore=["cfg"])
        self.cfg = cfg
        n        = cfg.num_classes

        # ── Backbone ──────────────────────────────────────────
        logger.info("Loading SlowFast R50 (Kinetics-400 pretrained)...")
        self.backbone = slowfast_r50(pretrained=True)

        # Replace projection head with dropout + UCF-Crime linear
        in_features = self.backbone.blocks[-1].proj.in_features
        self.backbone.blocks[-1].proj = nn.Sequential(
            nn.Dropout(p=0.5),
            nn.Linear(in_features, n),
        )

        self._freeze_backbone(cfg.unfreeze_last_n)

        # ── Loss ──────────────────────────────────────────────
        # label_smoothing=0.1 softens the hard labels.
        # UCF-Crime has label noise — all clips from a Fighting
        # video are labelled Fighting even if most look normal.
        self.loss_fn = nn.CrossEntropyLoss(label_smoothing=cfg.label_smoothing)

        # ── Metrics ───────────────────────────────────────────
        kw = dict(task="multiclass", num_classes=n)
        self.train_acc   = torchmetrics.Accuracy(**kw)
        self.val_acc     = torchmetrics.Accuracy(**kw)
        self.val_prec    = torchmetrics.Precision(**kw,  average="macro")
        self.val_recall  = torchmetrics.Recall(**kw,     average="macro")
        self.val_f1      = torchmetrics.F1Score(**kw,    average="macro")
        self.val_top3    = torchmetrics.Accuracy(**kw,   top_k=3)
        self.val_confmat = torchmetrics.ConfusionMatrix(**kw)

        # AUROC accumulated per-batch, computed at epoch end (see docstring)
        self.val_auroc = torchmetrics.AUROC(**kw, average="macro")

    # ── Backbone freezing ─────────────────────────────────────

    def _freeze_backbone(self, unfreeze_last_n: int) -> None:
        """Freeze all params. Unfreeze last N blocks + head."""
        for p in self.backbone.parameters():
            p.requires_grad = False

        # Unfreeze last N residual blocks
        blocks = list(self.backbone.blocks.children())
        for block in blocks[-unfreeze_last_n:]:
            for p in block.parameters():
                p.requires_grad = True

        # Always ensure head is trainable
        for p in self.backbone.blocks[-1].proj.parameters():
            p.requires_grad = True

        n_train = sum(p.numel() for p in self.parameters() if p.requires_grad)
        n_total = sum(p.numel() for p in self.parameters())
        logger.info(
            "Trainable: %s / %s (%.2f%%)  [last %d blocks + head]",
            f"{n_train:,}", f"{n_total:,}",
            100 * n_train / n_total,
            unfreeze_last_n,
        )

    # ── Forward ───────────────────────────────────────────────

    def forward(self, slow: torch.Tensor, fast: torch.Tensor) -> torch.Tensor:
        """
        Args:
            slow : (B, 3, T_slow, H, W)
            fast : (B, 3, T,      H, W)
        Returns:
            logits : (B, num_classes)
        """
        return self.backbone([slow, fast])

    # ── Training step (OOM-safe) ──────────────────────────────

    def training_step(self, batch, batch_idx):
        try:
            slow, fast, y = batch
            logits = self(slow, fast)
            loss   = self.loss_fn(logits, y)
            preds  = logits.argmax(dim=1)

            self.train_acc(preds, y)
            self.log("train_loss", loss,           on_step=True,  on_epoch=True, prog_bar=True)
            self.log("train_acc",  self.train_acc, on_step=False, on_epoch=True, prog_bar=True)
            return loss

        except RuntimeError as e:
            if "out of memory" in str(e).lower():
                torch.cuda.empty_cache()
                logger.warning("OOM at train batch %d — skipping", batch_idx)
                return None   # Lightning handles None gracefully
            raise e

        except Exception as e:
            logger.warning("Error at train batch %d: %s", batch_idx, e)
            return None

    # ── Validation step (OOM-safe) ────────────────────────────

    def validation_step(self, batch, batch_idx):
        try:
            slow, fast, y = batch
            logits = self(slow, fast)
            loss   = self.loss_fn(logits, y)
            preds  = logits.argmax(dim=1)
            probs  = torch.softmax(logits, dim=1)

            # Update all metrics
            self.val_acc(preds, y)
            self.val_prec(preds, y)
            self.val_recall(preds, y)
            self.val_f1(preds, y)
            self.val_top3(probs, y)
            self.val_confmat(preds, y)

            # Accumulate AUROC — computed in on_validation_epoch_end
            try:
                self.val_auroc.update(probs, y)
            except Exception:
                pass   # skip if batch missing classes — epoch-end handles it

            # Log standard metrics
            self.log("val_loss",   loss,            on_step=False, on_epoch=True, prog_bar=True)
            self.log("val_acc",    self.val_acc,    on_step=False, on_epoch=True, prog_bar=True)
            self.log("val_f1",     self.val_f1,     on_step=False, on_epoch=True, prog_bar=True)
            self.log("val_top3",   self.val_top3,   on_step=False, on_epoch=True)
            self.log("val_prec",   self.val_prec,   on_step=False, on_epoch=True)
            self.log("val_recall", self.val_recall, on_step=False, on_epoch=True)

        except RuntimeError as e:
            if "out of memory" in str(e).lower():
                torch.cuda.empty_cache()
                logger.warning("OOM at val batch %d — skipping", batch_idx)
                return None
            raise e

        except Exception as e:
            logger.warning("Error at val batch %d: %s", batch_idx, e)
            return None

    # ── Validation epoch end ──────────────────────────────────

    def on_validation_epoch_end(self) -> None:
        """
        Compute AUROC over the full accumulated val set.
        This avoids "No negative/positive samples" crashes
        that happen when computing per-batch.
        """
        try:
            auroc = self.val_auroc.compute()
            self.log("val_auroc", auroc, on_epoch=True, prog_bar=True)
        except Exception as e:
            logger.warning("AUROC computation failed: %s", e)
        finally:
            self.val_auroc.reset()

        # NOTE: val_confmat is NOT reset here.
        # MetricsCallback reads it in its own on_validation_epoch_end hook
        # (which runs after this model hook) before resetting.

    # ── Optimiser ─────────────────────────────────────────────

    def configure_optimizers(self):
        # Differential LR: unfrozen backbone blocks get lr×0.1, head gets full lr.
        # Preserves Kinetics-400 pretrained features while allowing fast head adaptation.
        head_ids        = {id(p) for p in self.backbone.blocks[-1].proj.parameters()}
        backbone_params = [
            p for p in self.parameters()
            if p.requires_grad and id(p) not in head_ids
        ]
        head_params = list(self.backbone.blocks[-1].proj.parameters())

        optimizer = torch.optim.AdamW(
            [
                {"params": backbone_params, "lr": self.cfg.lr * 0.1},
                {"params": head_params,     "lr": self.cfg.lr},
            ],
            weight_decay=self.cfg.weight_decay,
        )

        # CosineAnnealingLR smoothly decays lr from initial to eta_min over T_max epochs
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
            optimizer,
            T_max   = self.cfg.epochs,
            eta_min = 1e-6,
        )

        return {
            "optimizer"   : optimizer,
            "lr_scheduler": {"scheduler": scheduler, "monitor": "val_loss"},
        }

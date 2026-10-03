# Failed / aborted runs

Every failed, aborted or excluded run is listed here with its run id, date and reason.
| results/raw/pilot_dev_4b (dev) | 2026-10-02 20:0x | facts 20/20, history 20/20, tool 1/20 instances | Crashed: the block-value feature vector was extended (embedding similarity, a dev-time change) while the pilot was running; the next family's process loaded the new code against a value model fitted on the old features (14 vs 13 features). | Superseded by pilot2_dev_4b (refit with the new feature); facts/history rows of the first pilot are kept and reported as the pre-change dev iteration. |

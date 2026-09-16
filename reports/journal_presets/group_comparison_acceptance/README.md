# Group-comparison visual acceptance renders

6 presets x 17 synthetic datasets x 2 widths: PASS 196, WARN 4, FAIL 0.

Statistics enabled (auto test; post-hoc all pairs for 3+ groups). FAIL = overlapping text, clipped annotation or smallest text under 5 pt at the target width; WARN = legend over data or width off target by more than 15 %. Nothing auto-fixed. Every observation is drawn (n_points_drawn == n).

| preset | dataset | width | status | issues |
|---|---|---|---|---|
| gc_box_points_light | two_by_three | full_183mm | WARN | exported width 146.9 mm deviates -20% from target 183.0 mm  |
| gc_box_points_outline | two_by_three | full_183mm | WARN | exported width 146.9 mm deviates -20% from target 183.0 mm  |
| gc_dense_groups | two_by_three | full_183mm | WARN | exported width 146.9 mm deviates -20% from target 183.0 mm  |
| gc_violin_points | two_by_three | full_183mm | WARN | exported width 146.9 mm deviates -20% from target 183.0 mm  |

# KGnote design reference sources

This public index records reusable design lessons and public references. Private learning conversations, local filesystem locations, unpublished course-project files, and raw evaluation exports are intentionally not reproduced.

## Private source boundary

Some KGnote requirements were normalized from private learning sessions and earlier local prototypes. Their public authority is represented by the accepted requirements, scenarios, decision records, and product contracts in this repository. The original wording and local artifacts remain outside the public repository and are not required to build or review KGnote.

Reusable lessons retained from those private sources include:

- separate immutable Source/Evidence from Concept identity and Learning Overlay;
- retain confusion and correction history instead of replacing it with a mastery percentage;
- require dry-run, explicit consent, provenance, idempotency, and read-back around external I/O or canonical mutation;
- distinguish local engineering evidence from native-app, human-usability, and learning-effectiveness evidence;
- keep renderer-specific navigation separate from canonical knowledge relations.

These summaries do not grant redistribution rights to the original private materials and do not make historical implementation details normative.

## Public research references

The following sources provide adjacent evidence. They do not independently validate KGnote's complete product design.

### Concept and knowledge maps

- Novak, J. D., & Cañas, A. J. (2008). *The Theory Underlying Concept Maps and How to Construct and Use Them*. IHMC Technical Report. <https://cmap.ihmc.us/docs/theory-of-concept-maps>
- Davies, M. (2011). Concept mapping, mind mapping and argument mapping: what are the differences and do they matter? *Higher Education, 62*, 279–301. <https://doi.org/10.1007/s10734-010-9387-6>
- Nesbit, J. C., & Adesope, O. O. (2006). Learning With Concept and Knowledge Maps: A Meta-Analysis. *Review of Educational Research, 76*(3), 413–448. <https://doi.org/10.3102/00346543076003413>
- Chang, K. E., Sung, Y. T., & Chen, I. D. (2002). The Effect of Concept Mapping to Enhance Text Comprehension and Summarization. *The Journal of Experimental Education, 71*(1), 5–23. <https://doi.org/10.1080/00220970209602054>

### Prior knowledge and multiple representations

- Amadieu, F., Tricot, A., & Mariné, C. (2009). Prior knowledge in learning from a non-linear electronic document: Disorientation and coherence of the reading sequences. *Computers in Human Behavior, 25*(2), 381–388. <https://doi.org/10.1016/j.chb.2008.12.017>
- Ainsworth, S. (2006). DeFT: A conceptual framework for considering learning with multiple representations. *Learning and Instruction, 16*(3), 183–198. <https://doi.org/10.1016/j.learninstruc.2006.03.001>
- Schnotz, W., & Bannert, M. (2003). Construction and interference in learning from multiple representation. *Learning and Instruction, 13*(2), 141–156. <https://doi.org/10.1016/S0959-4752(02)00017-8>
- Chandler, P., & Sweller, J. (1992). The split-attention effect as a factor in the design of instruction. *British Journal of Educational Psychology, 62*(2), 233–246. <https://doi.org/10.1111/j.2044-8279.1992.tb01017.x>

### Retrieval practice

- Karpicke, J. D., & Blunt, J. R. (2011). Retrieval Practice Produces More Learning than Elaborative Studying with Concept Mapping. *Science, 331*(6018), 772–775. <https://doi.org/10.1126/science.1199327>

## Source adoption rules

- External material remains reference evidence, not permanent product authority.
- Before copying code or assets, record ownership or license, source revision, local modifications, and verification.
- Provider and platform behavior must be rechecked against current official documentation before implementation.
- No private source, credential, raw export, or machine-specific path belongs in the public repository.

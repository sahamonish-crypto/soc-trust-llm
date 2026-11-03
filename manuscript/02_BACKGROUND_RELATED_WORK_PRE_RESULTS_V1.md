# 2. Background and Related Work

**Draft status:** PRE-RESULTS / PRE-GATE-7  
**Citation notation:** `[P#]` refers to the numbered primary-paper corpus and will be converted to the target journal citation style later.

## 2.1 SOC Alert Triage and Analyst Workload

Security Operations Centers operate under conditions in which analysts must inspect and prioritize large numbers of alerts while maintaining sensitivity to relatively rare but consequential malicious activity. Prior research identifies alert volume, false positives, limited analyst capacity, and alert fatigue as persistent operational challenges [P6, P7]. These conditions create a decision environment in which automation may reduce repetitive work but can also introduce new verification demands.

Research on SOC alert prioritisation has therefore considered machine-learning, optimization, and human–AI approaches for identifying alerts that warrant analyst attention [P6, P25, P36]. This literature establishes that triage quality should not be evaluated solely through raw detection accuracy. Operational usefulness also depends on prioritisation behavior, false-positive burden, analyst workload, and the ability to preserve human oversight for ambiguous or consequential cases.

Human–AI teaming research in SOC environments further argues for systems that support analysts rather than simply replace them [P3–P5]. Such work motivates hybrid decision structures in which automation handles or summarizes information while analysts retain authority over consequential decisions. These studies provide an important foundation for the present work, but they also imply that evaluating an AI component in isolation is insufficient when the intended deployment context is collaborative.

## 2.2 Large Language Models in Security Operations

LLMs have been studied across a growing range of cybersecurity tasks, including alert classification and prioritisation, rule labeling, log interpretation, incident analysis, threat intelligence, and analyst-facing support [P1, P2, P24, P26–P28, P31, P32]. Systematic reviews increasingly describe LLMs as potentially useful interfaces between complex security telemetry and human operators, particularly when security information must be summarized or interpreted in natural language [P26–P28].

Direct SOC studies already demonstrate that LLM-based alert triage and human–LLM collaboration are established research areas rather than unexplored capabilities [P1, P2]. Accordingly, this study does not treat basic LLM use in SOC workflows as its novelty. Instead, these studies provide the technical and operational baseline from which questions about confidence, verification, and analyst reliance become important.

Retrieval-augmented approaches also show how an LLM can be supplied with security-relevant evidence from logs or incident context rather than generating an analysis from model parameters alone [P31]. Such architectures can improve traceability by linking model outputs to retrieved security context. However, evidence presentation and confidence communication are conceptually separate design dimensions: supporting evidence may help an analyst inspect the basis for a recommendation, whereas a confidence signal is intended to communicate uncertainty about whether the recommendation is correct.

The wider LLM cybersecurity literature additionally documents limitations involving hallucination, context sensitivity, inconsistent outputs, model variability, and evaluation difficulty [P26–P28]. These limitations reinforce the need for explicit evaluation boundaries and held-out testing when an LLM is used as a decision-support component.

## 2.3 Trust, Reliance, and Appropriate Use of Automation

Trust and reliance are related but should not be treated as interchangeable. Foundational work on trust in automation defines trust as an attitude toward an automated agent and emphasizes that the design objective should be appropriate rather than maximal trust [P22]. When trust exceeds system capability, users may over-rely on automation; when trust falls below capability, useful automation may be rejected or under-used.

This distinction is central to the present research because behavioral reliance can be observed directly from user decisions, whereas subjective trust reflects a psychological assessment of the system. A user may report high trust yet override a recommendation, or report skepticism while still following an AI suggestion in particular circumstances. Measuring only subjective trust would therefore provide an incomplete account of human–AI decision making.

Human–AI decision-support research has examined how model confidence, explanations, perceived capability, and uncertainty expressions influence reliance [P8–P10, P29]. These studies show that the presentation of uncertainty can alter user behavior, but they also caution against assuming that communicating uncertainty automatically produces appropriate reliance. The effect depends on the accuracy of the underlying confidence signal, the task, the user, and how the information is presented.

Cybersecurity introduces additional human-factors concerns. Research with cybersecurity professionals identifies automation bias, confirmation bias, explainability concerns, false-positive burden, and skepticism toward AI-generated alerts as relevant operational issues [P23]. These findings support the use of hybrid analyst–AI decision structures and motivate explicit study of when analysts accept or reject model recommendations.

## 2.4 LLM Confidence Estimation and Calibration

LLM-generated recommendations may be linguistically confident even when they are incorrect. Consequently, a model's textual style should not be treated as a calibrated probability of correctness. Confidence estimation seeks to construct a signal associated with the likelihood of correctness, whereas calibration evaluates whether numerical confidence corresponds appropriately to observed correctness frequencies [P30, P33–P35].

Several approaches have been proposed for estimating LLM uncertainty. These include verbalized self-confidence, probability-derived methods where model internals are available, repeated sampling, and measures based on agreement or consistency across multiple generations [P30, P33, P34]. For black-box or API-accessed models, consistency-based approaches are particularly attractive because they can be obtained without direct access to internal logits.

Sample-consistency research has shown that agreement across repeated generations can provide useful information about prediction reliability and can outperform some direct-confidence baselines on calibration tasks [P34]. Importantly, such findings do not imply that a particular consistency estimator will be calibrated in a new domain. Domain-specific evaluation on held-out labeled data remains necessary.

Calibration quality can be evaluated using several complementary measures. The Brier score directly measures squared error between predicted confidence and observed correctness and is suitable as a proper scoring rule for probabilistic predictions [P34, P35]. Expected Calibration Error and reliability diagrams provide additional information about correspondence between confidence levels and empirical correctness, although ECE is sensitive to binning decisions [P33–P35]. Discrimination metrics can separately evaluate whether confidence distinguishes correct from incorrect model predictions.

Post-hoc calibration methods such as logistic/Platt scaling or isotonic regression can transform a raw confidence signal using labeled development data [P33, P35]. Such mappings must themselves be fitted and selected without using the final evaluation set if the resulting evaluation is to remain meaningful.

## 2.5 From Machine Calibration to Human Reliance

Technical calibration and human trust calibration are related but distinct. A technically well-calibrated score concerns the statistical relationship between confidence and model correctness. Human trust calibration concerns whether a person's trust or reliance corresponds appropriately to the automation's capability [P22].

A confidence signal can therefore fail at multiple stages. The raw uncertainty estimator may provide little information about correctness; the estimator may discriminate useful cases but be numerically miscalibrated; a post-hoc mapping may improve numerical calibration but fail on new data; or a technically adequate confidence signal may be communicated in a way that users misunderstand or ignore. Conversely, a persuasive interface could increase reliance even when the confidence information itself is poorly calibrated.

This motivates separating the estimator, the calibrator, and the user-facing presentation. The current project evaluates the first two stages before freezing the final participant-facing intervention. This sequencing is intended to avoid designing the human experiment around a confidence mechanism that has not first demonstrated adequate held-out technical behavior.

## 2.6 Study Positioning and Research Gap

The relevant research areas are individually well established. Prior studies investigate LLM-assisted SOC work and alert triage [P1–P5], retrieval-augmented incident analysis [P31], human factors and trust in cybersecurity [P23], appropriate reliance on automation [P22, P29], and LLM confidence estimation and calibration [P30, P33–P35].

The research gap addressed by the current project therefore lies at their intersection rather than within any single component. Existing evidence does not by itself establish whether a confidence mechanism that is selected prospectively and evaluated on untouched SOC data can subsequently support appropriate behavioral reliance during analyst-facing alert triage.

The project addresses this question through a staged design. Technical model selection is separated from uncertainty estimation; uncertainty estimation is separated from calibration; calibration development is separated from untouched calibration evaluation; and these technical stages are separated from the later human study. The final participant-facing intervention will be defined only after the technical calibration stage has passed its predefined evaluation safeguard.

This structure is intended to support two forms of validity. First, technical conclusions about confidence quality are protected from direct tuning on the final calibration-EVAL set. Second, the later human study can evaluate the behavioral consequences of a previously selected technical mechanism rather than selecting that mechanism according to participant outcomes.

The final novelty statement will be written only after completion of the technical evaluation, finalization of the human-study protocol, and a fresh literature audit immediately before submission.

**RESULT-INDEPENDENT END OF BACKGROUND AND RELATED WORK DRAFT**

## Drafting constraints still in force

- No Gate 6D DEV result is reported.
- No calibration-EVAL result is reported.
- No human-study result is reported.
- No External-TEST result is reported.
- No final human-study conditions are specified.
- No final participant count is specified.
- No final questionnaire or NASA-TLX administration rule is specified.
- No definitive “first” novelty claim is made.

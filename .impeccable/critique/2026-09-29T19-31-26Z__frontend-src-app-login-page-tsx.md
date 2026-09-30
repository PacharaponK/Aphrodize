---
target: login and registration UX
total_score: 22
max_score: 40
na_heuristics: 
p0_count: 0
p1_count: 3
target_identity: "file:C:\\Users\\ACER\\Desktop\\Projects\\Aphrodize\\frontend\\src\\app\\login\\page.tsx"
target_fingerprint: "sha256:e61eed39a1642c97bbf1a799b7255a84f77c552798781b14434ae8a85fcc76ee"
target_path: "C:\\Users\\ACER\\Desktop\\Projects\\Aphrodize\\frontend\\src\\app\\login\\page.tsx"
timestamp: 2026-09-29T19-31-26Z
slug: frontend-src-app-login-page-tsx
---
# Login and registration UX critique

**Targets:** `frontend/src/app/login/page.tsx` and `frontend/src/app/signup/page.tsx`

**Method:** dual-agent (A: `/root/auth_review_a` · B: `/root/auth_evidence_b`)

## Design specificity

The calm dark brand panel, white form surface, and coral action fit a skin-wellness product. The “not a diagnosis” message and consent-before-face-analysis cue give Aphrodize some identity. Still, the split-form pattern could belong to almost any wellness app. The English eyebrow labels and “protocol เดิม” also make the experience feel less locally authored. The bigger mismatch is that the interface asks for sensitive health data without explaining the data use clearly at the point of consent.

**Automated scan and browser evidence:** The bundled detector returned `[]` (0 findings) for the login and signup markup. There were no detector findings or false positives to reconcile. Independent browser checks covered `/login` and the initial `/signup` account step at desktop and mobile sizes; console error logs were empty. No overlay was injected, so there is no user-visible overlay. Neither reviewer submitted a form or created an account; the later health questionnaire and error states were reviewed from source, not exercised live.

## Design health score

| # | Heuristic | Score | Key issue |
|---|---|---:|---|
| 1 | Visibility of system status | 3/4 | Submit states and wizard progress are shown. |
| 2 | Match with the real world | 2/4 | Thai labels are clear, but “protocol” and English eyebrow labels add friction. |
| 3 | User control and freedom | 2/4 | Back navigation exists, but health onboarding has no defer/skip route. |
| 4 | Consistency and standards | 3/4 | Familiar form patterns; language treatment is inconsistent. |
| 5 | Error prevention | 2/4 | Required fields and password matching help; consent scope remains unclear. |
| 6 | Recognition rather than recall | 3/4 | Inputs are labeled and use autocomplete; the question count is visible. |
| 7 | Flexibility and efficiency | 1/4 | Signup requires a long, sequential questionnaire with no alternative. |
| 8 | Aesthetic and minimalist design | 3/4 | Desktop hierarchy is calm; mobile hides useful reassurance. |
| 9 | Error recovery | 2/4 | Some signup failures have next steps, but login has no password recovery. |
| 10 | Help and documentation | 1/4 | No contextual explanation for the health questions or consent. |
| **Total** |  | **22/40 — Acceptable** | Significant improvements would reduce trust and completion friction. |

## Overall impression

The desktop login is clear and restrained. Registration is where confidence drops: users first accept a vague data-storage consent, then discover a long required health questionnaire. On mobile, the signup consent and submit button are below the first screen, so users must scroll before they can finish the account step. The biggest opportunity is to make the data request transparent and let people understand—and control—what is required before they commit.

## What works

- The desktop split layout separates product context from the task, and the primary action is easy to locate.
- Explicit labels, browser autocomplete, password confirmation, and a visible wizard progress indicator reduce common form friction.
- The copy avoids presenting face analysis as diagnosis and signals that image analysis requires consent.

## Priority issues

1. **[P1] Consent does not explain the data agreement.** The required signup checkbox references data storage, but the form does not visibly explain which profile/health data is collected, why it is needed, how it is handled, or how this differs from later face-analysis consent.
   - **Why it matters:** People are being asked to disclose sensitive health information without enough context to make an informed choice.
   - **Fix:** Add a concise data-use summary and privacy link beside consent; separate account/profile consent from face-analysis consent at the point it is requested. Explain guardian consent in the under-13 path as well.
   - **Suggested command:** `/impeccable clarify`
2. **[P1] Health onboarding is a mandatory gate before first use.** Signup moves from account details into 13 or 15 sequential health questions, with no skip/defer option, time estimate, or per-question reason. Some questions cover menstrual tracking, allergies, and irritation.
   - **Why it matters:** Users may abandon or feel pressured to disclose more than they expected before seeing the product’s value.
   - **Fix:** Create the account first, then offer progressive onboarding; identify optional answers and explain briefly why each sensitive question helps.
   - **Suggested command:** `/impeccable onboard`
3. **[P1] Login has no password-recovery route.** There is no visible “Forgot password?” action on `/login`.
   - **Why it matters:** A user who cannot remember a password has no self-service path back into the account.
   - **Fix:** Add a reset-password flow with clear confirmation, failure, and retry states.
   - **Suggested command:** `/impeccable harden`
4. **[P2] Mobile signup hides the action behind the fold.** At a 390×844 requested viewport (375px client width after scrollbar), the required consent begins around y=855 and the submit button around y=937. The consent row itself measures only 18px high. The desktop signup also has slight bottom overflow at 900px.
   - **Why it matters:** The user reaches the end of the visible fields without seeing the consent or the action needed to continue; the checkbox is a small touch target.
   - **Fix:** Reduce vertical pressure on small screens, keep the consent label comfortably tappable, and ensure the primary action is visible or clearly signposted after the final field.
   - **Suggested command:** `/impeccable layout`
5. **[P2] Mixed-language and technical copy interrupts comprehension.** Labels such as “WELLNESS SKIN TRACKING,” “FIRST-TIME SETUP,” and “WELCOME BACK” appear beside Thai copy, while “protocol เดิม” is technical and unexplained.
   - **Why it matters:** The user has to switch language and infer what “protocol” means during a trust-sensitive flow.
   - **Fix:** Localize the eyebrow labels and replace “protocol” with plain Thai that describes the comparison conditions.
   - **Suggested command:** `/impeccable clarify`

## Cognitive-load check

Two of eight checks failed, indicating moderate cognitive load:

- **Fail — choices:** The wizard presents one question at a time, but select menus open to as many as seven choices.
- **Pass — memory bridge:** Answers remain available while the page stays mounted, and users can go back. A refresh/interruption may lose progress.
- **Pass — navigation:** The wizard shows the current question and progress.
- **Fail — jargon:** English eyebrow labels and “protocol เดิม” interrupt an otherwise Thai flow.
- **Pass — visual noise:** The desktop page is uncluttered.
- **Pass — pattern consistency:** Controls follow familiar form conventions.
- **Pass — task focus:** The wizard isolates one question at a time.
- **Pass mechanically — context switching:** The route stays in place; the missing consent explanation can still leave users uncertain.

## Emotional journey and persona red flags

- **Jordan, first-timer:** Registration does not set expectations for how many questions follow, how long they take, or which answers are optional. “protocol เดิม” is unclear.
- **Sam, accessibility-dependent:** Fields and controls have labels, but the wizard changes questions without an apparent focus move or explicit live announcement. This is a source-based concern, not a screen-reader test.
- **Casey, interrupted mobile user:** Consent and submit fall below the initial mobile viewport. Signup answers and credentials remain in page state, so leaving or refreshing may discard progress.

Signup begins with a clear next step, but then turns into a sensitive-data gate. The missing “why we ask” context and the lack of save-and-return make interruption feel costly.

## Minor observations

- Login errors are generic, and the password hint does not summarize all password requirements.
- The select fields contain several choices once opened; help text could make the expected answer clearer.
- `/signup` browser review stopped before the questionnaire because reaching it would require submitting account details.

## Questions to consider

- What is the minimum profile needed before a person can start tracking?
- Which health questions must be answered up front, and which can wait until the user sees the benefit?
- Can the mobile signup explain data use at the exact point where consent is collected?

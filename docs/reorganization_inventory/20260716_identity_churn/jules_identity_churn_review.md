# Identity Churn Review Report
**Date:** 2026-07-16
**Reviewer:** Jules

## 1. Findings and Assessment of ID Replacements
After reviewing the fuzzy matches and unpaired additions/removals, it is clear that the generated CSV artifacts attempt to replace YouTube user-upload artifacts (e.g., "AnnaR21", "shinemyshoes", "NightwolfX19") and topic-channel uploads with cleaned, canonical metadata.

However, because the source audio files are likely tied to these unofficial uploads, overwriting the database metadata and IDs wholesale would incorrectly assert these files are verified official releases. The text cleanup should not be treated as verified identity metadata.

## 2. Classification of Possible Matches

### Recording ID Matches
*   **R618E648C5DF8 -> RC8001438B328** (Cinephile - NightwolfX19 upload vs clean Cinephile): **cover/unofficial upload/topic-channel artifact**
*   **R2790098D186D -> R2FBF40F92458** (Blundetto - Topic vs Blundetto): **cover/unofficial upload/topic-channel artifact**
*   **R6362791F591D -> R3E45CED9EA79** (Fred again.. text cleanup): **likely same musical work but ambiguous recording/release identity**
*   **R816AF6C09817 -> R4CEC369080D7** (Stephane Pompougnac diacritic fix): **safe replacement** (minor text correction)
*   **RB3A064EA5B1D -> R9C3221F9E35D** (Eden (Official Video) vs Eden): **cover/unofficial upload/topic-channel artifact**
*   **RDCF76F602036 -> R52FAB4F3674A** (Tinlicker - Topic vs Tinlicker, Helsloot): **cover/unofficial upload/topic-channel artifact**
*   **RDD34966D304F -> R2AC5379CE153** (Lapalux [Unbelievable Music Video] vs clean): **cover/unofficial upload/topic-channel artifact**
*   **RE698A7E5FEFA -> RFA0429E86F7D** (R.I.O. feat. U-Jean feat arrangement): **likely same musical work but ambiguous recording/release identity**

### Song ID Matches
*   **S8A1E9B16012E -> S4EFF2A7F27DA** (Cinephile - NightwolfX19): **cover/unofficial upload/topic-channel artifact**
*   **S00862A8E5645 -> SACBC51F96979** (Lapalux [Unbelievable Music Video]): **cover/unofficial upload/topic-channel artifact**
*   **S1D8A6053AEC9 -> S43C3FE151CB2** (Tinlicker - Topic): **cover/unofficial upload/topic-channel artifact**
*   **S6ED56FDD0B8A -> SF07CF1ABB616** (Stephane Pompougnac): **safe replacement**
*   **SB59CD753BA6A -> S27CAC610D7BB** (R.I.O. feat. U-Jean): **likely same musical work but ambiguous recording/release identity**
*   **SBEA0D88D2E04 -> SB29C8C8F69AD** (Fred again..): **likely same musical work but ambiguous recording/release identity**

## 3. Review of Current Recommendation
The current recommendation ("Do not promote generated CSV files wholesale. Keep scalar cleanup/warning patches, but do not accept ID churn without source-backed review.") is **correct**. Wholesale promotion of the generated CSV files would result in unsafe identity churn, losing the provenance of unofficial YouTube uploads and dropping valid manual additions.

## 4. Patch Manifest Recommendations
*   **Reject**: `recordings_id_replacements.csv`, `songs_id_replacements.csv`, `external_link_id_replacements.csv`, `main_database_changed_rows_added.csv`, and `main_database_changed_rows_removed.csv`. These files represent wholesale CSV rewrites that introduce unsafe ID churn.
*   **Adjust/Create**: A new warning flags patch should be created. Instead of replacing the rows, we should append ambiguity warnings to the existing rows in the main database indicating that the metadata is derived from a user upload or topic channel.

## 5. Exact Rows/IDs Requiring Manual Review
The following removed manual additions (found in `recordings_unpaired_removed.csv`) must be manually reviewed and restored, as they were lost in the rebuild process:
*   R05508169FA85 (Kenny Dale - ONLY LOVE CAN BREAK A HEART)
*   R0C9415AEA0F8 (The Floaters - FLOAT ON)
*   R12515F7EA52B (Redbone - COME AND GET YOUR LOVE)
*   R1E043250C17C (Van McCoy - THE HUSTLE)
*   R2BAE99C1A65C (Shocking Blue - VENUS)
*   R32C04DD18577 (Free - ALL RIGHT NOW)
*   R331388112725 (Nazareth - LOVE HURTS)
*   R3C99D3C52014 (Santa Esmeralda - DON'T LET ME BE MISUNDERSTOOD)
*   R3DB5153CBED5 (Starland Vocal Band - AFTERNOON DELIGHT)
*   R454A67C04A2F (Alicia Bridges - I LOVE THE NIGHTLIFE)
*   R4B86B89FE61B (Warren Zevon - WEREWOLVES OF LONDON)
*   R4D6DF7B0631F (Frijid Pink - HOUSE OF THE RISING SUN)
*   R4EE4E6793CC9 (Mungo Jerry - IN THE SUMMERTIME)
*   R625320511A66 (Wild Cherry - PLAY THAT FUNKY MUSIC)
*   R7600565AE17F (The Knack - MY SHARONA)
*   R7712B649AF0B (Ace Frehley - NEW YORK GROOVE)
*   R7CF4113089FB (Blues Image - RIDE CAPTAIN RIDE)
*   R850482D08F96 (Paper Lace - THE NIGHT CHICAGO DIED)
*   R9AAB3AB230F6 (Roxy Music - LOVE IS THE DRUG)
*   RA773D16F4B04 (Carl Douglas - KUNG FU FIGHTING)
*   RA8B1F48F1815 (Lipps Inc. - FUNKYTOWN)
*   RB2F301762660 (Gregg Allman - MIDNIGHT RIDER)
*   RB47932A3B4D9 (Bobby Bloom - MONTEGO BAY)
*   RBE8C7F71DE74 (King Harvest - DANCING IN THE MOONLIGHT)
*   RC450FCDA3C58 (Harry Chapin - CAT'S IN THE CRADLE)
*   RCB09B7283A2F (Mountain - MISSISSIPPI QUEEN)
*   RD4B9807DDF8F (Vicki Lawrence - THE NIGHT THE LIGHTS WENT OUT IN GEORGIA)
*   RDD6DEB95F439 (Crosby, Stills, Nash & Young - OHIO)
*   RDEE792B035B2 (Pilot - MAGIC)
*   RDF3604DAA9AA (Cheryl Lynn - GOT TO BE REAL)
*   REEC3A14E08AE (Looking Glass - BRANDY (YOU'RE A FINE GIRL))
*   RF82EEFEBCDCF (M - POP MUZIK)

In addition, the original versions of the unofficial uploads (e.g., NightwolfX19, shinemyshoes, AnnaR21) should be reviewed to see if the files can be replaced with official verified audio.

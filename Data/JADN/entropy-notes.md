
JADN models information as defined in information theory, to represent the amount of "news" or
"essential information" contained in a message. 

Information defines significant vs. insignificant in lexical values. Just as whitespace
is often insignificant at the data level, an information model defines significance at the logical
level: any data that is not included in a logical value is insignificant and has been ignored
in the lexical to logical conversion.

Information theory uses the word "entropy" to refer to the quantity of information carried in a
message. The more restrictions that are placed on a value, the less data is required to
carry its information regardless of how much data is actually used. Strings with no restrictions
are least efficient; strings with restricted length, character set, or patterns are more efficient,
and enumerations such as field names, enumerated map keys, and vocabularies are by far the most
efficient.  The string "mitigation" is always the same at the data level, but when it represents
one of only five possible observation types
("ssp-statement-issue", "control-objective", "mitigation", "finding", "historic") it carries
less than 3 bits of information in 80 bits of lexical data.
The other 77 bits are not essential content and are not included in the logical value.
If an information model allows generic strings (for example, "Purina-cat-chow" or
"Four score and seven years ago our fathers brought forth on this continent a new nation,
from the 🏔️ to the 🌾 to the 🏖️.") where restricted or enumerated values are appropriate,
it requires both users and applications to deal with inappropriate content and presents a
larger attack surface to adversaries.
Designing information models to correctly distinguish between essential content and
insignificant data is not just theoretical trivia, it's an operational and security benefit.
Allowing a tokenized Gettysburg address as a telephone number type is an anti-pattern that
can be tested for in the release pipeline.
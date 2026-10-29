"""Words the API shows to students and parents, in English and Malayalam.

The web app sends the reader's language in the Accept-Language header ("en"
or "ml"). Logs, decisions and audits always keep the English wording, so a
teacher or auditor reads the same record whatever language the student uses.

The Malayalam here was written for Class 9 students and their parents, in
plain everyday words. A Malayalam teacher should check it before the pilot.
"""

from fastapi import Header

LANGS = ("en", "ml")

MESSAGES: dict[str, dict[str, str]] = {
    # --- Sign-in and passwords
    "err.wrong_login": {
        "en": "Wrong username or password",
        "ml": "യൂസർനെയിമോ പാസ്‌വേഡോ തെറ്റാണ്",
    },
    "err.too_many_tries": {
        "en": "Too many tries. Please wait 15 minutes, or ask your school to reset your password.",
        "ml": "ഒരുപാട് തവണ ശ്രമിച്ചു. 15 മിനിറ്റ് കാത്തിരിക്കൂ, അല്ലെങ്കിൽ പുതിയ പാസ്‌വേഡിനായി സ്കൂളിനോട് ചോദിക്കൂ.",
    },
    "err.current_password": {
        "en": "Your current password is not right",
        "ml": "ഇപ്പോഴത്തെ പാസ്‌വേഡ് ശരിയല്ല",
    },
    "err.same_password": {
        "en": "Choose a password different from the old one",
        "ml": "പഴയതിൽ നിന്ന് വ്യത്യസ്തമായ ഒരു പാസ്‌വേഡ് തിരഞ്ഞെടുക്കൂ",
    },
    "err.waiting_consent": {
        "en": "Waiting for a parent or guardian to give consent",
        "ml": "രക്ഷിതാവിന്റെ അനുമതിക്കായി കാത്തിരിക്കുന്നു",
    },
    # --- Ask SYNiq
    "err.tutor_too_long": {
        "en": "Please ask a question of up to 600 characters",
        "ml": "600 അക്ഷരങ്ങൾ വരെയുള്ള ഒരു ചോദ്യം ചോദിക്കൂ",
    },
    "err.tutor_daily_limit": {
        "en": "That's a lot of questions for one day. Try the explanations, or ask your teacher.",
        "ml": "ഇന്നത്തേക്ക് ഒരുപാട് ചോദ്യങ്ങളായി. വിശദീകരണങ്ങൾ നോക്കൂ, അല്ലെങ്കിൽ ടീച്ചറോട് ചോദിക്കൂ.",
    },
    "err.tutor_unavailable": {
        "en": "The tutor isn't available right now. The explanations and hints still work.",
        "ml": "ട്യൂട്ടർ ഇപ്പോൾ ലഭ്യമല്ല. വിശദീകരണങ്ങളും സൂചനകളും പ്രവർത്തിക്കും.",
    },
    "tutor.declined": {
        "en": "I can't help with that one. Let's get back to the topic. What part would you like me to explain?",
        "ml": "അതിൽ എനിക്ക് സഹായിക്കാൻ കഴിയില്ല. നമുക്ക് പാഠത്തിലേക്ക് തിരിച്ചുവരാം. ഏത് ഭാഗമാണ് വിശദീകരിക്കേണ്ടത്?",
    },
    "tutor.distress": {
        "en": (
            "I'm really glad you told me. This is important, and you deserve help from a person who can be there for you. "
            "Please talk to a teacher, a parent, or another adult you trust today. "
            "You can also call Tele-MANAS on 14416 at any time, free. It's a helpline where you can talk to someone who "
            "understands. If you are in danger right now, call 112."
        ),
        "ml": (
            "ഇത് എന്നോട് പറഞ്ഞതിന് നന്ദി. ഇത് വളരെ പ്രധാനപ്പെട്ട കാര്യമാണ്. നിങ്ങളുടെ കൂടെ നിൽക്കാൻ കഴിയുന്ന ഒരാളുടെ സഹായം "
            "നിങ്ങൾക്ക് കിട്ടണം. ഇന്നുതന്നെ ഒരു ടീച്ചറോടോ രക്ഷിതാവിനോടോ നിങ്ങൾ വിശ്വസിക്കുന്ന മറ്റൊരു മുതിർന്നയാളോടോ സംസാരിക്കൂ. "
            "ഏതു സമയത്തും Tele-MANAS ഹെൽപ്‌ലൈനിൽ 14416 എന്ന നമ്പറിൽ സൗജന്യമായി വിളിക്കാം. നിങ്ങളെ മനസ്സിലാക്കുന്ന ഒരാളോട് "
            "അവിടെ സംസാരിക്കാം. ഇപ്പോൾ അപകടത്തിലാണെങ്കിൽ 112-ൽ വിളിക്കൂ."
        ),
    },
    # --- Check-ins and answers
    "checkin.not_saved": {
        "en": "Thanks. Check-ins are not saved for your account.",
        "ml": "നന്ദി. നിങ്ങളുടെ അക്കൗണ്ടിൽ ചെക്ക്-ഇന്നുകൾ സേവ് ചെയ്യുന്നില്ല.",
    },
    "checkin.thanks": {"en": "Thanks for telling me.", "ml": "പറഞ്ഞതിന് നന്ദി."},
    "checkin.thanks_low": {
        "en": "Thanks for telling me. We can start with something short, and you can take a break any time.",
        "ml": "പറഞ്ഞതിന് നന്ദി. നമുക്ക് ചെറിയ എന്തെങ്കിലും കൊണ്ട് തുടങ്ങാം. എപ്പോൾ വേണമെങ്കിലും ഇടവേള എടുക്കാം.",
    },
    "feedback.correct": {"en": "Correct, well done.", "ml": "ശരിയാണ്, നന്നായി ചെയ്തു."},
    "feedback.not_yet": {"en": "Not quite yet.", "ml": "ഇതുവരെ ശരിയായില്ല."},
    "parent.progress_note": {
        "en": "Progress labels are estimates from practice so far, not test results.",
        "ml": "ഇതുവരെയുള്ള പരിശീലനത്തിൽ നിന്നുള്ള ഏകദേശ കണക്കാണിത്, പരീക്ഷാഫലമല്ല.",
    },
    # --- Why the next step was chosen (engine/rules.py), by rule id
    "reason.R1_prereq_gap": {
        "en": "This topic builds on an earlier one that may need a quick refresh first.",
        "ml": "ഈ പാഠം മുമ്പത്തെ ഒരു പാഠത്തെ ആശ്രയിച്ചാണ്. ആദ്യം അത് ഒന്ന് ഓർമ്മ പുതുക്കാം.",
    },
    "reason.R2_struggle_new_format": {
        "en": "The last few answers suggest a different explanation might help.",
        "ml": "അവസാനത്തെ കുറച്ച് ഉത്തരങ്ങൾ കണ്ടിട്ട്, മറ്റൊരു രീതിയിലുള്ള വിശദീകരണം സഹായിച്ചേക്കും.",
    },
    "reason.R3_spaced_review": {
        "en": "A quick review now helps you remember this for longer.",
        "ml": "ഇപ്പോൾ ഒന്ന് ആവർത്തിച്ചാൽ ഇത് കൂടുതൽ കാലം ഓർമ്മയിൽ നിൽക്കും.",
    },
    "reason.R4_introduce": {
        "en": "Starting a new topic with an explanation.",
        "ml": "പുതിയ പാഠം ഒരു വിശദീകരണത്തോടെ തുടങ്ങുന്നു.",
    },
    "reason.R5_chapter_complete": {
        "en": "Every topic in this chapter looks secure.",
        "ml": "ഈ അധ്യായത്തിലെ എല്ലാ പാഠങ്ങളും നന്നായി ഉറച്ചതായി തോന്നുന്നു.",
    },
    "reason.R6_practice": {
        "en": "Practice at a level that matches where you are now.",
        "ml": "ഇപ്പോഴത്തെ നിലയ്ക്ക് ചേരുന്ന പരിശീലനം.",
    },
    "reason.student_choice": {
        "en": "The student asked for this explanation style.",
        "ml": "ഈ രീതിയിലുള്ള വിശദീകരണം നിങ്ങൾ തന്നെ തിരഞ്ഞെടുത്തു.",
    },
    # --- Support SYNiq noticed (engine/detect.py)
    "announce.focus": {
        "en": "From now on I'll show things in shorter steps, one at a time, with quick challenges. {reason}",
        "ml": "ഇനി മുതൽ കാര്യങ്ങൾ ചെറിയ പടികളായി, ഒന്നൊന്നായി, ചെറിയ ചലഞ്ചുകളോടെ കാണിക്കാം. {reason}",
    },
    "announce.easy_read": {
        "en": "From now on I'll use shorter lines and read things aloud to you. {reason}",
        "ml": "ഇനി മുതൽ ചെറിയ വരികൾ ഉപയോഗിക്കുകയും ഉറക്കെ വായിച്ചുതരികയും ചെയ്യാം. {reason}",
    },
    "announce.small_steps": {
        "en": "From now on I'll show sums with pictures and smaller numbers first. {reason}",
        "ml": "ഇനി മുതൽ കണക്കുകൾ ആദ്യം ചിത്രങ്ങളും ചെറിയ സംഖ്യകളും വെച്ച് കാണിക്കാം. {reason}",
    },
    "announce.switch_off": {
        "en": "You can switch this off in Settings.",
        "ml": "ഇത് സെറ്റിങ്സിൽ ഓഫ് ചെയ്യാം.",
    },
    "noticed.small_steps.basic": {
        "en": "Counting and number steps have tripped you up a few times, and pictures help with those.",
        "ml": "എണ്ണുന്നതിലും സംഖ്യകളുടെ പടികളിലും കുറച്ചു തവണ തെറ്റുപറ്റി. അവയ്ക്ക് ചിത്രങ്ങൾ സഹായിക്കും.",
    },
    "noticed.small_steps.pictures": {
        "en": "Pictures and smaller numbers have helped you more than long explanations.",
        "ml": "നീണ്ട വിശദീകരണങ്ങളേക്കാൾ ചിത്രങ്ങളും ചെറിയ സംഖ്യകളുമാണ് നിങ്ങളെ കൂടുതൽ സഹായിച്ചത്.",
    },
    "noticed.easy_read.long": {
        "en": "Long questions have been harder for you than short ones on the same ideas.",
        "ml": "ഒരേ ആശയങ്ങളിൽ, ചെറിയ ചോദ്യങ്ങളേക്കാൾ നീണ്ട ചോദ്യങ്ങളാണ് നിങ്ങൾക്ക് കൂടുതൽ പ്രയാസമായത്.",
    },
    "noticed.easy_read.read_aloud": {
        "en": "You often use read aloud, so I'll do it for you.",
        "ml": "നിങ്ങൾ പലപ്പോഴും ഉറക്കെ വായിക്കൽ ഉപയോഗിക്കുന്നു. അതുകൊണ്ട് ഞാൻ തന്നെ വായിച്ചുതരാം.",
    },
    "noticed.focus.slipping": {
        "en": "Your answers tend to slip later in a session, so shorter bursts should help.",
        "ml": "ഒരു സെഷന്റെ അവസാനമാകുമ്പോൾ ഉത്തരങ്ങൾ തെറ്റാൻ തുടങ്ങുന്നു. അതുകൊണ്ട് ചെറിയ ഭാഗങ്ങളായി ചെയ്യുന്നത് സഹായിക്കും.",
    },
    "noticed.focus.breaks": {
        "en": "You've been taking breaks, so I'll keep things short.",
        "ml": "നിങ്ങൾ ഇടവേളകൾ എടുക്കുന്നുണ്ട്. അതുകൊണ്ട് കാര്യങ്ങൾ ചെറുതാക്കി വെക്കാം.",
    },
    # --- Responses to answers (engine/responses.py)
    "resp.cheer.0": {"en": "Nice work!", "ml": "നന്നായി!"},
    "resp.cheer.1": {"en": "Correct, well done.", "ml": "ശരിയാണ്, നന്നായി ചെയ്തു."},
    "resp.cheer.2": {"en": "Yes! That's it.", "ml": "അതെ! അതുതന്നെ."},
    "resp.cheer.3": {"en": "Great thinking.", "ml": "നല്ല ചിന്ത!"},
    "resp.correct_short": {"en": "⭐ Correct!", "ml": "⭐ ശരി!"},
    "resp.not_yet": {
        "en": "Not quite yet. Let's look at it together.",
        "ml": "ഇതുവരെ ശരിയായില്ല. നമുക്ക് ഒരുമിച്ച് നോക്കാം.",
    },
    "why.count_it_out": {
        "en": "Seeing it with objects often makes a mistake easy to spot.",
        "ml": "വസ്തുക്കൾ വെച്ച് കാണുമ്പോൾ തെറ്റ് എളുപ്പം കണ്ടുപിടിക്കാം.",
    },
    "why.step_by_step": {
        "en": "Going through it one step at a time shows exactly where it changed.",
        "ml": "ഓരോ പടിയായി ചെയ്യുമ്പോൾ എവിടെയാണ് മാറിയതെന്ന് കൃത്യമായി കാണാം.",
    },
    "why.real_life": {
        "en": "This has been tricky a few times, so here it is as an everyday story.",
        "ml": "ഇത് കുറച്ചു തവണ പ്രയാസമായി. അതുകൊണ്ട് ഇതാ ഒരു നിത്യജീവിത കഥയായി.",
    },
    "why.try_similar": {
        "en": "Several tries have not worked yet, so here is a smaller one with the same idea.",
        "ml": "കുറച്ചു ശ്രമങ്ങൾ ശരിയായില്ല. അതുകൊണ്ട് ഇതേ ആശയമുള്ള ഒരു ചെറിയ ചോദ്യം ഇതാ.",
    },
    "mistake.subtracted_instead": {
        "en": "It looks like you took away instead of adding.",
        "ml": "കൂട്ടുന്നതിന് പകരം കുറച്ചതായി തോന്നുന്നു.",
    },
    "mistake.added_not_subtracted": {
        "en": "It looks like you added instead of taking away.",
        "ml": "കുറയ്ക്കുന്നതിന് പകരം കൂട്ടിയതായി തോന്നുന്നു.",
    },
    "mistake.multiplied_instead": {
        "en": "It looks like you multiplied instead of adding.",
        "ml": "കൂട്ടുന്നതിന് പകരം ഗുണിച്ചതായി തോന്നുന്നു.",
    },
    "mistake.added_not_multiplied": {
        "en": "It looks like you added instead of multiplying.",
        "ml": "ഗുണിക്കുന്നതിന് പകരം കൂട്ടിയതായി തോന്നുന്നു.",
    },
    "mistake.one_group_off": {
        "en": "You have one group too many or too few.",
        "ml": "ഒരു കൂട്ടം കൂടുതലോ കുറവോ ആയിപ്പോയി.",
    },
    "mistake.one_group_only": {
        "en": "It looks like you counted only one of the groups.",
        "ml": "ഒരു കൂട്ടം മാത്രമേ എണ്ണിയുള്ളൂ എന്ന് തോന്നുന്നു.",
    },
    "mistake.counting_slip": {
        "en": "So close! You are just 1 away. Count once more, slowly.",
        "ml": "വളരെ അടുത്തെത്തി! 1 മാത്രമേ വ്യത്യാസമുള്ളൂ. ഒന്നുകൂടി പതുക്കെ എണ്ണിനോക്കൂ.",
    },
    "mistake.digits_swapped": {
        "en": "You have the right digits, but in the wrong order.",
        "ml": "അക്കങ്ങൾ ശരിയാണ്, പക്ഷേ ക്രമം തെറ്റിപ്പോയി.",
    },
    "mistake.tens_slip": {
        "en": "The ones are right. Check the tens again.",
        "ml": "ഒറ്റയുടെ സ്ഥാനം ശരിയാണ്. പത്തിന്റെ സ്ഥാനം ഒന്നുകൂടി നോക്കൂ.",
    },
    "mistake.more": {
        "en": "Your answer is {n} more than it should be.",
        "ml": "നിങ്ങളുടെ ഉത്തരം ശരിയുത്തരത്തേക്കാൾ {n} കൂടുതലാണ്.",
    },
    "mistake.less": {
        "en": "Your answer is {n} less than it should be.",
        "ml": "നിങ്ങളുടെ ഉത്തരം ശരിയുത്തരത്തേക്കാൾ {n} കുറവാണ്.",
    },
    "pic.you_wrote": {"en": "What you wrote", "ml": "നിങ്ങൾ എഴുതിയത്"},
    "pic.right_way": {"en": "The right way", "ml": "ശരിയായ വഴി"},
    "pic.start_with": {"en": "Start with {a}", "ml": "ആദ്യം {a}"},
    "pic.take_away": {"en": "Take away {b}", "ml": "{b} കുറയ്ക്കൂ"},
    "pic.group": {"en": "Group {i}", "ml": "കൂട്ടം {i}"},
    "pic.share": {"en": "Share {i}", "ml": "പങ്ക് {i}"},
    "pic.alt_add": {"en": "{x} plus {y} makes {r}", "ml": "{x}, കൂടെ {y}, ആകെ {r}"},
    "pic.alt_cross_out": {"en": "cross out {b}, and {left} are left", "ml": "{b} എണ്ണം വെട്ടിക്കളയുക, ബാക്കി {left}"},
    "pic.tip_add": {
        "en": "Count every object in both groups: {a} and then {b} more makes {r}.",
        "ml": "രണ്ടു കൂട്ടത്തിലെയും എല്ലാം എണ്ണിനോക്കൂ: {a}, പിന്നെ {b} കൂടി ചേർന്നാൽ {r}.",
    },
    "pic.tip_subtract": {
        "en": "Cross out {b} and count what is left: {r}.",
        "ml": "{b} എണ്ണം വെട്ടിക്കളഞ്ഞ് ബാക്കിയുള്ളത് എണ്ണൂ: {r}.",
    },
    "pic.tip_multiply": {
        "en": "{b} groups of {a} make {r}. Count the groups, then count every object.",
        "ml": "{a} വീതമുള്ള {b} കൂട്ടങ്ങൾ ചേർന്നാൽ {r}. ആദ്യം കൂട്ടങ്ങൾ എണ്ണൂ, പിന്നെ ഓരോന്നും എണ്ണൂ.",
    },
    "pic.tip_divide": {
        "en": "Share {a} equally into {b} groups. Each group gets {r}.",
        "ml": "{a}-നെ {b} കൂട്ടങ്ങളായി തുല്യമായി പങ്കിടൂ. ഓരോ കൂട്ടത്തിനും {r} കിട്ടും.",
    },
    "story.add": {
        "en": "You have {a} mangoes. Your friend gives you {b} more. Now you have {a} + {b} = {r} mangoes.",
        "ml": "നിങ്ങളുടെ കയ്യിൽ {a} മാങ്ങയുണ്ട്. ഒരു സുഹൃത്ത് {b} മാങ്ങ കൂടി തരുന്നു. ഇപ്പോൾ {a} + {b} = {r} മാങ്ങ.",
    },
    "story.subtract": {
        "en": "There are {a} bananas in a bunch. You share {b} with your family. {a} − {b} = {r} bananas are left.",
        "ml": "ഒരു കുലയിൽ {a} പഴമുണ്ട്. അതിൽ {b} എണ്ണം വീട്ടുകാർക്ക് കൊടുക്കുന്നു. {a} − {b} = {r} പഴം ബാക്കി.",
    },
    "story.multiply": {
        "en": "There are {b} plates with {a} appams on each. Altogether that is {b} × {a} = {r} appams.",
        "ml": "{b} പ്ലേറ്റുകളിൽ ഓരോന്നിലും {a} അപ്പം വീതമുണ്ട്. ആകെ {b} × {a} = {r} അപ്പം.",
    },
    "story.divide": {
        "en": "{a} sweets are shared equally among {b} friends. Each friend gets {a} ÷ {b} = {r} sweets.",
        "ml": "{a} മിഠായി {b} കൂട്ടുകാർക്ക് തുല്യമായി പങ്കിടുന്നു. ഓരോരുത്തർക്കും {a} ÷ {b} = {r} മിഠായി കിട്ടും.",
    },
    "step.read": {"en": "Read the question: {sum}.", "ml": "ചോദ്യം വായിക്കൂ: {sum}."},
    "step.work": {"en": "Work it out: {sum} = {r}.", "ml": "കണക്കുകൂട്ടൂ: {sum} = {r}."},
    "resp.worked_answer": {"en": "The worked answer: {solution}", "ml": "ചെയ്തുകാണിച്ച ഉത്തരം: {solution}"},
    "resp.easier_next": {
        "en": "Let's look at the worked answer, then try an easier one next.",
        "ml": "ചെയ്തുകാണിച്ച ഉത്തരം നോക്കാം. എന്നിട്ട് അടുത്തത് ഒരു എളുപ്പമുള്ളത് ചെയ്യാം.",
    },
    "resp.what_is": {"en": "What is {sum}?", "ml": "{sum} എത്ര?"},
    "resp.quick_challenge": {"en": "Quick challenge: {sum} = ?", "ml": "ചെറിയൊരു ചലഞ്ച്: {sum} = ?"},
    # --- Tips for common mistakes in the demo maths chapter (routers/student.py)
    "tip.square_each_term": {
        "en": "Squaring a sum is not the same as squaring each part: (a + b)² also has a middle term, 2ab.",
        "ml": "ഒരു തുകയുടെ വർഗം, ഓരോ ഭാഗത്തിന്റെയും വർഗം കൂട്ടുന്നതല്ല: (a + b)²-ൽ 2ab എന്ന നടുവിലെ പദവും ഉണ്ട്.",
    },
    "tip.missing_double": {
        "en": "Check the middle term: it is 2ab, twice the product of the two terms.",
        "ml": "നടുവിലെ പദം നോക്കൂ: അത് 2ab ആണ്, രണ്ട് പദങ്ങളുടെ ഗുണനഫലത്തിന്റെ ഇരട്ടി.",
    },
    "tip.sign_middle": {
        "en": "In (a − b)² the middle term is negative: −2ab.",
        "ml": "(a − b)²-ൽ നടുവിലെ പദം ന്യൂനസംഖ്യയാണ്: −2ab.",
    },
    "tip.sign_last": {
        "en": "The last term is b², and a square is never negative.",
        "ml": "അവസാന പദം b² ആണ്. ഒരു വർഗം ഒരിക്കലും ന്യൂനസംഖ്യയാകില്ല.",
    },
    "tip.sum_not_difference": {
        "en": "(a + b)(a − b) gives a difference of squares, a² − b², so the result has a minus sign.",
        "ml": "(a + b)(a − b) വർഗങ്ങളുടെ വ്യത്യാസമാണ്, a² − b². അതുകൊണ്ട് ഉത്തരത്തിൽ മൈനസ് ചിഹ്നമുണ്ട്.",
    },
    "tip.extra_middle_term": {
        "en": "In (a + b)(a − b) the middle terms cancel out, so there is no middle term.",
        "ml": "(a + b)(a − b)-ൽ നടുവിലെ പദങ്ങൾ പരസ്പരം ഇല്ലാതാകും. അതുകൊണ്ട് നടുവിലെ പദമില്ല.",
    },
    "tip.product_terms": {
        "en": "Multiply every term in the first bracket by every term in the second.",
        "ml": "ആദ്യത്തെ ബ്രാക്കറ്റിലെ ഓരോ പദത്തെയും രണ്ടാമത്തേതിലെ ഓരോ പദം കൊണ്ടും ഗുണിക്കൂ.",
    },
    "tip.arithmetic": {
        "en": "The method looks right; check the arithmetic in the last step.",
        "ml": "രീതി ശരിയാണെന്ന് തോന്നുന്നു. അവസാന പടിയിലെ കണക്കുകൂട്ടൽ ഒന്നുകൂടി നോക്കൂ.",
    },
}


def t(lang: str, key: str, **values) -> str:
    """The message in this language, falling back to English."""
    entry = MESSAGES[key]
    return entry.get(lang, entry["en"]).format(**values)


def has(key: str) -> bool:
    return key in MESSAGES


def language(accept_language: str | None = Header(default=None)) -> str:
    """FastAPI dependency: "ml" if the reader asked for Malayalam, otherwise "en"."""
    first = (accept_language or "").split(",")[0].strip().lower()
    return "ml" if first.startswith("ml") else "en"


_ENGLISH_TO_KEY = {v["en"]: k for k, v in MESSAGES.items()}


def translate_english(lang: str, text: str) -> str:
    """Translate a stored English message (e.g. a reason saved before languages existed)."""
    key = _ENGLISH_TO_KEY.get(text)
    return t(lang, key) if key and lang != "en" else text

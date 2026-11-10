"use client";

import Link from "next/link";
import { useSession } from "@/lib/session";

const EN = {
  back: "← My children",
  title: "SYNiq for parents",
  intro: "SYNiq is a learning app your child uses in the school computer lab. Here is what you can do with your own login.",
  sections: [
    ["What you see", "Each child's last 7 days in words, the topics they are learning, what helps them understand, and mistakes that keep coming back. There are no marks and no ranking."],
    ["What you can change", "The permissions (learning, mood check-ins, sharing with the school, thinking puzzles) and help such as screen-reader support, calm lessons or bigger buttons. Open Settings and permissions under your child's name. Changes work at once."],
    ["Helping at home", "Ask your child to explain one topic to you in their own words. Praise trying, not getting it right. A mistake is how SYNiq finds the next step."],
    ["Your child's data", "SYNiq keeps answers and progress so lessons can adapt. It shows no adverts and sells nothing. You can ask the school for a copy of everything it holds about your child, or ask for your child to be withdrawn, which deletes it."],
    ["Forgotten password", "Ask the school office. They give you a new temporary one, and you choose your own when you sign in."],
  ],
};

const ML = {
  back: "← എന്റെ കുട്ടികൾ",
  title: "രക്ഷിതാക്കൾക്കായി SYNiq",
  intro: "സ്കൂൾ കമ്പ്യൂട്ടർ ലാബിൽ നിങ്ങളുടെ കുട്ടി ഉപയോഗിക്കുന്ന പഠന ആപ്പാണ് SYNiq. നിങ്ങളുടെ സ്വന്തം ലോഗിനിൽ ചെയ്യാവുന്നത് ഇവയാണ്.",
  sections: [
    ["നിങ്ങൾ കാണുന്നത്", "ഓരോ കുട്ടിയുടെയും കഴിഞ്ഞ 7 ദിവസം വാക്കുകളിൽ, പഠിക്കുന്ന വിഷയങ്ങൾ, മനസ്സിലാക്കാൻ സഹായിക്കുന്നത്, ആവർത്തിക്കുന്ന തെറ്റുകൾ. മാർക്കോ റാങ്കോ ഇല്ല."],
    ["നിങ്ങൾക്ക് മാറ്റാവുന്നത്", "അനുമതികൾ (പഠനം, മൂഡ് ചെക്ക്-ഇൻ, സ്കൂളുമായി പങ്കുവെക്കൽ, ചിന്താ പസിലുകൾ), സ്ക്രീൻ റീഡർ സഹായം, ശാന്തമായ പാഠങ്ങൾ, വലിയ ബട്ടണുകൾ പോലുള്ള സഹായങ്ങൾ. കുട്ടിയുടെ പേരിന് താഴെയുള്ള ക്രമീകരണങ്ങളും അനുമതികളും തുറക്കൂ. മാറ്റങ്ങൾ ഉടൻ പ്രാബല്യത്തിൽ വരും."],
    ["വീട്ടിൽ സഹായിക്കാൻ", "ഒരു വിഷയം സ്വന്തം വാക്കുകളിൽ വിശദീകരിക്കാൻ കുട്ടിയോട് പറയൂ. ശരിയാക്കിയതിനല്ല, ശ്രമിച്ചതിനെ അഭിനന്ദിക്കൂ. തെറ്റുകളിലൂടെയാണ് SYNiq അടുത്ത പടി കണ്ടെത്തുന്നത്."],
    ["കുട്ടിയുടെ വിവരങ്ങൾ", "പാഠങ്ങൾ അനുയോജ്യമാക്കാൻ SYNiq ഉത്തരങ്ങളും പുരോഗതിയും സൂക്ഷിക്കുന്നു. പരസ്യങ്ങളില്ല, ഒന്നും വിൽക്കുന്നില്ല. കുട്ടിയെക്കുറിച്ച് സൂക്ഷിക്കുന്ന എല്ലാ വിവരങ്ങളുടെയും പകർപ്പ് സ്കൂളിനോട് ചോദിക്കാം, അല്ലെങ്കിൽ കുട്ടിയെ പിൻവലിക്കാൻ ആവശ്യപ്പെടാം; അപ്പോൾ അവ മായ്ക്കും."],
    ["പാസ്‌വേഡ് മറന്നാൽ", "സ്കൂൾ ഓഫീസിനോട് ചോദിക്കൂ. അവർ ഒരു താൽക്കാലിക പാസ്‌വേഡ് തരും; സൈൻ ഇൻ ചെയ്യുമ്പോൾ നിങ്ങളുടെ സ്വന്തം പാസ്‌വേഡ് തിരഞ്ഞെടുക്കാം."],
  ],
};

const HI = {
  back: "← मेरे बच्चे",
  title: "माता-पिता के लिए SYNiq",
  intro: "SYNiq सीखने का एक ऐप है जिसे आपका बच्चा इस्तेमाल करता है। अपने लॉगिन से आप ये कर सकते हैं।",
  sections: [
    ["आप क्या देखते हैं", "हर बच्चे के पिछले 7 दिन शब्दों में, वह कौन-से विषय सीख रहा है, उसे समझने में क्या मदद करता है, और बार-बार होने वाली गलतियाँ। कोई अंक नहीं, कोई रैंक नहीं।"],
    ["आप क्या बदल सकते हैं", "अनुमतियाँ (सीखना, मन की स्थिति के सवाल, स्कूल के साथ साझा करना, सोचने वाली पहेलियाँ) और मदद जैसे स्क्रीन रीडर, शांत पाठ या बड़े बटन। अपने बच्चे के नाम के नीचे 'सेटिंग्स और अनुमतियाँ' खोलें। बदलाव तुरंत लागू होते हैं।"],
    ["घर पर मदद", "बच्चे से कहें कि कोई एक विषय आपको अपने शब्दों में समझाए। सही होने की नहीं, कोशिश की तारीफ़ करें। गलती से ही SYNiq अगला कदम ढूँढता है।"],
    ["आपके बच्चे का डेटा", "पाठ बच्चे के हिसाब से ढल सकें, इसके लिए SYNiq उत्तर और प्रगति रखता है। कोई विज्ञापन नहीं, कुछ बेचा नहीं जाता। आप बच्चे के बारे में रखी हर जानकारी की कॉपी माँग सकते हैं, या बच्चे को हटाने को कह सकते हैं, जिससे वह जानकारी मिटा दी जाती है।"],
    ["पासवर्ड भूल गए", "स्कूल ऑफ़िस से (या परिवार खाते में खाता बनाने वाले से) पूछें। वे एक अस्थायी पासवर्ड देंगे, और साइन इन करते समय आप अपना पासवर्ड चुन लेंगे।"],
  ],
};

/** For parents, in their language: what SYNiq shows them and what they can change. */
export default function ParentHelp() {
  const { lang } = useSession();
  const w = lang === "ml" ? ML : lang === "hi" ? HI : EN;
  return (
    <div className="wrap help-page" lang={lang}>
      <p>
        <Link href="/parent">{w.back}</Link>
      </p>
      <h1>{w.title}</h1>
      <p>{w.intro}</p>
      {w.sections.map(([head, body]) => (
        <section key={head}>
          <h2>{head}</h2>
          <p>{body}</p>
        </section>
      ))}
    </div>
  );
}

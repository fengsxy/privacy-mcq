import csv

cases = [
    {
        "name": "Zoom Attendee Tracking",
        "design_purpose": "Design an attendee attention tracking feature for a video conferencing application.",
        "data_practice": """Zoom is a video conferencing platform which has seen a huge increase in usage and revenue since the beginning of the COVID-19 pandemic and has rapidly iterated its product to accommodate this growing user base. Zoom developed a feature that allowed the host to monitor the attendees' attention: if Zoom was not the application in focus on a participant's computer for over 30 seconds while someone else was sharing their screen, Zoom showed a clock icon next to the participant's name in the participant panel. At the end of each meeting, Zoom also generated a report for the host listing the percentage of time each participant had the presentation window in focus during the meeting. This feature received significant backlash after launch. The Zoom team later apologized for falling short of the community's privacy and security expectations and decided to remove the attention tracker feature permanently.""",
        "key_questions": [
            "Opt-in or Opt-out?",
            "When should we send notification? Just-in-time, Install time, or Periodically?",
            "Only present aggregated data?",
            "Only enable the feature in the education setting?",
            "More salient notification? Always on?",
            "How to infer attention? Using a camera?",
            "Process data on the edge?",
            "Data retention? Where is data stored?",
            "Who can access the data? Attention Data Access control?",
            "Report attention prediction errors?",
            "Data collection interval?",
            "Data deletion request?",
            "What if I accidentally accept it? How to fix it?"
        ]
    },
    {
        "name": "Facebook Cambridge Analytics",
        "design_purpose": "Design a third-party application integration system that allows apps to collect and use user data from a social media platform.",
        "data_practice": """Facebook allowed third-party developers to collect user data through apps and quizzes, including not just the data of users who installed these apps, but also the data of their Facebook friends. Cambridge Analytica, a political consulting firm, obtained data from up to 87 million Facebook users through a personality quiz app called "this is your digital life" developed by researcher Aleksandr Kogan. While only around 270,000 users installed the app, Cambridge Analytica gained access to millions more users' data through Facebook's friend data sharing API policy at the time. The firm used this data to create psychological profiles of voters, which were then used to target political advertisements during the 2016 US presidential election and other political campaigns. When this practice was exposed in 2018, it led to widespread criticism of Facebook's data sharing policies, multiple investigations, and eventually resulted in Facebook paying a $5 billion fine to the FTC. Facebook subsequently changed its policies to restrict third-party access to user data and implemented stricter data sharing controls.""",
        "key_questions": [
            "What data can third-party apps access? Whose data?",
            "Granularity of permissions?",
            "What is the default permission state?",
            "Access control mechanism?",
            "Does it require consent for all data subjects involved?",
            "Can users selectively grant access to specific data categories?",
            "What information is disclosed during the consent process?",
            "How can users review and revoke permissions?",
            "Audits/reviews on data usage of third-party apps?",
            "Data deletion request?",
            "Restriction on data retention period?",
            "Restriction on secondary use of data?",
            "Restriction on data sharing with external parties?"
        ]
    },
    {
        "name": "AirTag",
        "design_purpose": "Design a real-time location tracking system for personal items.",
        "data_practice": """Apple's AirTag, launched in 2021, is a small tracking device designed to help users locate personal items through Apple's Find My network. The device leverages a network of over a billion Apple devices worldwide to relay location data. When an AirTag is separated from its owner, it can communicate with nearby Apple devices, which then anonymously relay the AirTag's location back to the owner. While intended for finding lost items, the technology has been misused for unauthorized tracking of individuals. Reports emerged of AirTags being secretly placed in cars, bags, or personal belongings to track people's movements. Although Apple implemented various safety features like alerting iPhone users of unknown AirTags traveling with them and making AirTags play a sound after being away from their owner, concerns persisted about the delayed notifications (originally 72 hours, later reduced to a random time between 8-24 hours) and the fact that Android users initially had no way to detect AirTags. Apple later released an Android app called "Tracker Detect" and enhanced their safety features.""",
        "key_questions": [
            "Which location technologies (GPS, Bluetooth, WiFi) should be used?",
            "Is the location data anonymized?",
            "Should tracking be continuous or only activated when requested?",
            "How frequently is location data updated?",
            "Where is location history stored? Data retention period?",
            "How is location data encrypted in transit and at rest?",
            "How to notify others near a tracked item? When?",
            "How can other users check if they are being tracked?",
            "How should other users disable the tracking if they found unknown tracking devices?",
            "Who can access location history? Access control?",
            "Data deletion request?"
        ]
    },
    {
        "name": "Target Pregnancy Prediction",
        "design_purpose": "Design a retail analytics system that processes customer purchase histories to automatically generate personalized coupons and recommendations.",
        "data_practice": """In 2012, Target's marketing analytics team developed a pregnancy prediction score system that could identify pregnant customers based on their shopping patterns. The system analyzed purchase history and assigned each customer a "pregnancy prediction" score by identifying approximately 25 products that, when analyzed together, allowed Target to predict not only pregnancy but also estimate the customer's due date. Key indicators included sudden purchases of unscented lotions, supplements like calcium and magnesium, and large bags of cotton balls in specific sequences. Target then used these predictions to send targeted pregnancy and baby-related marketing materials to these customers. The practice gained public attention when Target inadvertently revealed a teenage girl's pregnancy to her father by sending baby-related coupons to their house before she had told her family. After this incident and subsequent public backlash, Target modified their marketing approach to mix pregnancy-related advertisements with unrelated products to make their targeting less obvious, rather than abandoning the practice entirely.""",
        "key_questions": [
            "What customer data is collected? Include personal identifier information?",
            "Combine data from different sources?",
            "Data retention period?",
            "Is purchase history tracking opt-in or opt-out?",
            "How is consent obtained for personalized recommendations?",
            "Review/delete what data is collected?",
            "How is the data processed to generate personalized recommendations?",
            "Exclude life events/conditions for predictive analytics?",
            "Exclude certain types of purchases from analysis?",
            "Can customers opt-out of specific types of predictions?",
            "Who can view the coupons and recommendations? Access control?"
        ]
    },
    {
        "name": "Facebook Emotional Contagion",
        "design_purpose": "Design a research experiment to study how exposure to emotional content affects users' own emotional expressions on a social media platform.",
        "data_practice": """In 2014, Facebook conducted a psychological experiment on 689,003 users without their explicit consent by manipulating their News Feed content to study emotional contagion. For one week in January 2012, Facebook's algorithm selectively removed either positive or negative emotional content from users' News Feeds. Users in the positive condition saw fewer negative posts, while those in the negative condition saw fewer positive posts. The researchers then analyzed these users' subsequent posts to see if reducing exposure to certain emotional content would affect their own emotional expressions. The study found that users who saw fewer negative posts wrote more positive posts, and those who saw fewer positive posts wrote more negative posts, demonstrating that emotional states could be transferred through social networks. When the study was published, it sparked significant controversy over research ethics, particularly regarding informed consent and the manipulation of users' emotional states. While Facebook defended the research as covered under their data use policy, the incident led to discussions about the ethics of large-scale social experiments on unwitting platform users and resulted in changes to Facebook's research review processes.""",
        "key_questions": [
            "How are the participants selected for the control/experimental group?",
            "How long is the study?",
            "What data is collected? Anonymized?",
            "How long is experimental data retained? What happens to the data after the study?",
            "How is the data processed?",
            "How is emotional content selected? How to determine levels of emotional manipulation?",
            "Does it require informed consent from participants?",
            "How to handle withdrawal of consent?",
            "When and how is the manipulation disclosed?",
            "Limits on negative content manipulation?",
            "Identify and exclude vulnerable populations?",
            "Any deception? How to ensure it is ethically justified?",
            "Review the experiment?",
            "Who can access the user data? Access control?"
        ]
    },
      {
        "name": "Google Buzz",
        "design_purpose": "Design a system that integrates email services with social networking functionality.",
        "data_practice": """In 2010, Google launched Buzz, a social networking service integrated directly into Gmail. During its automatic setup process, Buzz created a public profile for Gmail users and automatically connected them with people they frequently emailed or chatted with, making these connections publicly visible by default. The system exposed users' most frequent Gmail contacts as public "followers," without adequately informing users or obtaining their consent. This was particularly problematic for individuals like journalists, professionals, or abuse survivors whose email contact lists contained sensitive relationships. For example, one blogger discovered that Buzz had publicly exposed her follower list, which included her abusive ex-boyfriend and his friends. Google initially defended the auto-following feature as enhancing user experience but quickly faced widespread criticism and several privacy complaints. Within days, Google made multiple changes to the privacy settings and eventually shut down Buzz in 2011. The incident resulted in an FTC settlement requiring Google to implement a comprehensive privacy program and undergo regular privacy audits for 20 years.""",
        "key_questions": [
            "Opt-in / Opt-out?",
            "Automatically enrolled / Suggestions?",
            "What user data is available to the public?",
            "Who can view the user contact lists by default?",
            "How can users control their contact list visibility?",
            "How to manage different types of contact groups?",
            "What data is combined across services?",
            "Review/delete data between services?",
            "How to obtain informed consent from users?",
            "Privacy audits?"
        ]
    },
    {
        "name": "OKCupid Score Manipulation",
        "design_purpose": "Design a research experiment to study how displayed compatibility scores influence user behavior and interactions on a dating platform.",
        "data_practice": """In 2014, OKCupid conducted experiments on its users by deliberately providing incorrect compatibility scores. The dating platform typically shows users a "match percentage" based on their answers to personality questions. During the experiment, OKCupid deliberately altered these scores, showing some users who were poor matches (30%) as excellent matches (90%), and vice versa. The platform then analyzed how the manipulated scores affected user behavior and interaction rates. When users were told they were highly compatible, they were more likely to engage in conversation and exchange contact information, even if their actual compatibility was low. OKCupid's co-founder Christian Rudder publicly defended these experiments in a blog post titled "We Experiment On Human Beings!", arguing that such testing was necessary for improving the service. The revelation sparked debates about informed consent in platform experiments, though the practice received less public backlash than similar experiments by other platforms.""",
        "key_questions": [
            "How are the participants selected for the control/experimental group? Opt-in / Opt-out?",
            "How long is the study?",
            "What data is collected? Anonymized?",
            "How long is experimental data retained? What happens to the data after the study?",
            "Are users informed about potential data manipulation?",
            "When and how is the manipulation disclosed to users?",
            "How to handle withdrawal of consent?",
            "Ethical review of the research process?",
            "How to identify and exclude vulnerable users?",
            "Who can access the experiment data? Access control?",
            "Any deception? How to ensure it is ethically justified?"
        ]
    },
    {
        "name": "Uber Price Discrimination",
        "design_purpose": "Design a dynamic pricing system for a ride-sharing service.",
        "data_practice": """Uber's pricing algorithm has been found to potentially factor in users' phone battery levels when determining ride prices. The app, which requires battery level access to implement power-saving features, could detect when a user's phone was running low on battery. Research suggested that users with low battery levels might be charged higher prices, potentially exploiting their increased urgency to secure a ride before their phone dies. This practice raised concerns about the ethical implications of using battery status data to influence pricing decisions, especially since users in more vulnerable situations (low battery) could be charged premium rates. When this practice was revealed, it sparked discussions about the boundaries of acceptable data usage in dynamic pricing systems and the need for transparency in how personal device data influences service costs.""",
        "key_questions": [
            "What data is collected? Anonymized?",
            "How long is the data retained?",
            "What factors should be excluded from pricing algorithms (e.g., personal user attributes)?",
            "How to communicate all pricing factors to users?",
            "Can users opt-out of optional data collection / mask certain status indicators?",
            "What oversight for pricing algorithms?"
        ]
    },
    {
        "name": "Staples Price Discrimination",
        "design_purpose": "Design an e-commerce pricing system that incorporates geographic and market data.",
        "data_practice": """Staples.com implemented location-based pricing by using visitors' IP addresses to estimate their distance from competing brick-and-mortar stores. The website would display different prices for identical products based on the customer's proximity to competitors' stores. If a customer was detected to be far from a competing store, they were shown higher prices, while those near competitors saw lower prices. The Wall Street Journal investigation found price differences of up to 10% between locations. When customers noticed these discrepancies and compared prices across different locations, it led to public backlash over the fairness of this digital price discrimination practice.""",
        "key_questions": [
            "What data is collected? Anonymized?",
            "How long is the data retained?",
            "What factors should be excluded from pricing algorithms?",
            "How to communicate all pricing factors to users?",
            "Can users opt-out of optional data collection / mask certain status indicators?",
            "What oversight for pricing algorithms?"
        ]
    },
    {
        "name": "Expedia Price Discrimination",
        "design_purpose": "Design a dynamic pricing system for a travel booking platform.",
        "data_practice": """Expedia's website employed a dynamic pricing system that displayed different hotel rates based on user characteristics such as the type of device used for browsing. The system could show varying prices for the same hotel room when accessed from different devices (e.g., Mac vs. Windows computers). When users logged into their Expedia accounts, the displayed prices could also differ based on their booking history and member status. A 2012 investigation found that Mac users were sometimes shown higher-priced hotel options compared to Windows users viewing the same search results. When this practice became public, it highlighted how e-commerce platforms can use device fingerprinting and user data to implement differential pricing strategies.""",
        "key_questions": [
            "What data is collected? Anonymized?",
            "How long is the data retained?",
            "What factors should be excluded from pricing algorithms?",
            "How to communicate all pricing factors to users?",
            "Can users opt-out of optional data collection / mask certain status indicators?",
            "What oversight for pricing algorithms?"
        ]
    },
    {
        "name": "Healthcare Price Discrimination",
        "design_purpose": "Design a healthcare billing system that processes patient financial information while maintaining compliance with healthcare billing regulations.",
        "data_practice": """Healthcare providers implemented systems that selectively waived patient copayments based on financial data. Their practice management software processed patient information including income level, payment history, and insurance status to determine copayment waiver eligibility. The system could flag patients who might qualify for financial assistance and automatically calculate adjusted payment amounts. Some providers used this data to routinely waive copayments for certain patient categories, while still billing insurance companies for the full amount. When insurance companies analyzed claims data patterns, they identified instances where providers consistently waived copayments for some patients while collecting them from others, raising questions about billing practices and insurance reimbursement.""",
        "key_questions": [
            "What patient financial data is collected and processed?",
            "How is sensitive financial information protected?",
            "What factors determine copayment waiver eligibility?",
            "How is the waiver decision process documented?",
            "Who has access to patient financial data?",
            "How long is financial data retained?",
            "How can patients review their financial information?",
            "What mechanisms exist for correcting errors in financial data?",
            "How is compliance with healthcare billing regulations ensured?",
            "What audit trails are maintained for pricing decisions?"
        ]
    }
]

# Function to format key questions
def format_key_questions(questions):
    return '\n'.join(f"{i+1}. {q}" for i, q in enumerate(questions))

# Write to CSV
with open('privacy_cases.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(['Case', 'Design Purpose', 'Data Practice', 'Key Questions'])
    
    for case in cases:
        writer.writerow([
            case['name'],
            case['design_purpose'],
            case['data_practice'],
            format_key_questions(case['key_questions'])
        ])

print("CSV file has been created successfully with all cases.")
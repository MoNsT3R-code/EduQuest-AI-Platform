# EduQuest-AI-Platform
An AI-powered gamified learning platform for grades 3–7 that uses Random Forest classification to predict student performance from behavioral telemetry data. Automatically adapts curriculum difficulty and gamified reward tiers in real-time to optimize personalized early childhood education.
# EduQuest AI: AI-Powered Gamified Learning Platform

An AI-powered gamified learning platform for grades 3–7 that uses Random Forest classification to predict student performance from behavioral telemetry data. Automatically adapts curriculum difficulty and gamified reward tiers in real-time to optimize personalized early childhood education.

---

## 👥 Project Contributors
* **Amzi Asif** (ID: 281133626)
* **Musfira Sehar** (ID: 280048443)

**Institution:** Forman Christian College University (FCCU)  
**Course:** Introduction to Artificial Intelligence  

---

## 🎯 Project Overview & Vision
Traditional educational platforms often apply a rigid, one-size-fits-all approach that fails to align with an individual student's unique learning pace. This frequently results in early disengagement or cognitive overload, particularly for younger learners in **Grades 3–7**. 

**EduQuest AI** addresses this problem by treating real-time student app interactions as behavioral telemetry. By running an ensemble **Machine Learning pipeline**, the platform continuously assesses student engagement levels and dynamically maps them to personalized gamified interfaces, ensuring that no student is left behind.

---

## 📊 Dataset Architecture & Feature Engineering

The system uses a dataset consisting of **200 student records** engineered with realistic academic variance and locked under a replication seed (`random_state=42`) to model classroom behavior.

### 🧪 Tracked Features
1. **Quiz Scores ($Q_s$):** Gauges short-term conceptual retention (0–100%).
2. **Assignments Completed ($A_c$):** Tracks homework milestone progression.
3. **Streak Days ($D_s$):** Measures consecutive days of app engagement (habit loops).
4. **Time Spent ($T_s$):** Tracks total hours spent inside learning modules.
5. **Total Attempts:** Logs repetitive interactions, signaling perseverance or confusion.
6. **Hints Used:** Measures a student's dependency on assistive guidance.

### 🧮 Weighted Labeling Logic
Ground-truth performance profiles are engineered dynamically using a weighted composite behavioral formula:

$$S = 0.4(Q_s) + 0.3(A_c) + 0.2(D_s) + 0.1(T_s)$$

The composite score ($S$) determines the student's operational tier:
* 🥇 **High Performance:** $S > 65$ (Triggers advanced enrichment pathways)
* 🥈 **Medium Performance:** $51 \le S \le 65$ (Triggers standard adaptive pacing)
* 🥉 **Low Performance:** $S \le 50$ (Triggers foundational support alerts)

---

## 🤖 Machine Learning Pipeline

The backend predictive core is powered by a **Random Forest Classifier** selected for its robustness against single-tree overfitting and its ability to handle complex, non-linear correlations in student data.

### ⚙️ Model Configurations:
* **Train/Test Split:** 80% Training Pool (160 samples) / 20% Testing Validation Pool (40 samples).
* **Strategy:** Stratified splitting to preserve absolute class proportions.
* **Estimator Volume:** 100 independent decision trees running bootstrap bagging.

### 📈 Model Evaluation Metrics
The predictive engine achieved an **Overall Test Accuracy of 72.50%** with the following validation matrix:

| Performance Class | Precision | Recall | F1-Score |
| :--- | :---: | :---: | :---: |
| 🥇 **High Performance** | 0.89 | 0.80 | 0.84 |
| 🥈 **Low Performance** | 0.73 | 0.73 | 0.73 |
| 🥉 **Medium Performance** | 0.62 | 0.67 | 0.65 |
| **Overall Accuracy** | | | **72.50%** |

---

## 🎮 The Gamified Reward Engine

EduQuest AI uses the model's live profile inferences to dynamically adjust the platform's gamified environment:

* **Gold Scholar Badge (High Tier):** Automatically scales up challenge levels, unlocking complex critical-thinking puzzles and peer-mentorship leaderboard tracking.
* **Silver Star Badge (Medium Tier):** Focuses on consistency loops, offering streak multiplier bonuses and targeted mini-milestones to motivate progression to the upper tier.
* **Bronze Beginner Badge (Low Tier):** *Framed entirely as a supportive launchpad.* The UI removes countdown timers, scales down cognitive load, and provides animated walkthroughs that reward effort and consistency over high scores.

---

## 💻 Technical Installation & Setup

This platform features an interactive user dashboard built using **Streamlit** for live telemetry adjustments and real-time model inferences.

### 🛠️ Prerequisites
Make sure you have Python 3.8+ installed on your local machine.

1. **Clone the Repository:**
   ```bash
   ```bash
   git clone [https://github.com/MoNsT3R-code/EduQuest-AI-Platform.git](https://github.com/MoNsT3R-code/EduQuest-AI-Platform.git)
   cd EduQuest-AI-Platform


   pip install pandas numpy scikit-learn streamlit matplotlib seaborn

   python eduquest_engine.py

   streamlit run app.py
  

   

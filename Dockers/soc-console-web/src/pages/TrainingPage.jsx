import React, { useState } from "react";
import TrainingHomePage from "../components/training/TrainingHomePage.jsx";
import TrainingConfigPage from "../components/training/TrainingConfigPage.jsx";
import TrainingRunPage from "../components/training/TrainingRunPage.jsx";
import TrainingResultPage from "../components/training/TrainingResultPage.jsx";

export default function TrainingPage() {
  const [step, setStep] = useState("home"); // home | config | run | result
  const [sessionId, setSessionId] = useState(null);

  return (
    <>
      {step === "home" && (
        <TrainingHomePage
          onStart={() => setStep("config")}
          onOpenResult={(sid) => {
            setSessionId(sid);
            setStep("result");
          }}
        />
      )}

      {step === "config" && (
        <TrainingConfigPage
          onBack={() => setStep("home")}
          onCreatedSession={(sid) => {
            setSessionId(sid);
            setStep("run");
          }}
        />
      )}

      {step === "run" && sessionId && (
        <TrainingRunPage
          sessionId={sessionId}
          onFinish={() => setStep("result")}
        />
      )}

      {step === "result" && sessionId && (
        <TrainingResultPage
          sessionId={sessionId}
          onBackHome={() => setStep("home")}
          onRestart={() => setStep("config")}
        />
      )}
    </>
  );
}
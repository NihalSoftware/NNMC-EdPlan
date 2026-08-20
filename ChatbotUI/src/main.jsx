import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import toast, { Toaster, ToastBar } from "react-hot-toast";
import App from "./App.jsx";
import AppErrorBoundary from "./components/common/AppErrorBoundary.jsx";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")).render(
  <AppErrorBoundary>
    <BrowserRouter>
      <App />
      <Toaster
      position="bottom-left"
      toastOptions={{
        duration: 3500,
        style: {
          fontSize: "16px",
          padding: "14px",
          width: "250px",
          boxShadow: "0 8px 24px rgba(0, 0, 0, 0.25)",
        },
        error: {
          duration: 3500,
          style: {
            background: "#ff4d4f",
            color: "#fff",
            fontSize: "16px",
            padding: "14px",
            width: "250px",
          },
        },
      }}
    >
      {(currentToast) => (
        <ToastBar toast={currentToast} position="bottom-left">
          {({ icon, message }) => (
            <>
              {currentToast.type === "error" ? (
                <button
                  type="button"
                  aria-label="Dismiss error message"
                  title="Dismiss error message"
                  onClick={() => toast.dismiss(currentToast.id)}
                  style={{
                    alignItems: "center",
                    background: "transparent",
                    border: 0,
                    cursor: "pointer",
                    display: "flex",
                    flexShrink: 0,
                    justifyContent: "center",
                    padding: 0,
                  }}
                >
                  {icon}
                </button>
              ) : (
                icon
              )}
              {message}
            </>
          )}
        </ToastBar>
      )}
      </Toaster>
    </BrowserRouter>
  </AppErrorBoundary>
);

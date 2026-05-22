import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./styles.css";

const img = new Image();
img.src = "/background.jpg";
img.onload = () => document.body.classList.add("has-custom-bg");

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

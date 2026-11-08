import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import "bootstrap/dist/css/bootstrap.min.css";
import "maplibre-gl/dist/maplibre-gl.css";
import "./styles.css";

import HospitalMap from "./HospitalMap";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <HospitalMap />
  </StrictMode>,
);

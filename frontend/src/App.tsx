import { Route, Routes } from "react-router-dom";
import AppLayout from "./layouts/AppLayout";
import Analytics from "./pages/Analytics";
import Dashboard from "./pages/Dashboard";
import HideFile from "./pages/HideFile";
import RecoverFile from "./pages/RecoverFile";
import TransferDetails from "./pages/TransferDetails";

export default function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route index element={<Dashboard />} />
        <Route path="hide" element={<HideFile />} />
        <Route path="recover" element={<RecoverFile />} />
        <Route path="analytics" element={<Analytics />} />
        <Route path="transfers/:transferId" element={<TransferDetails />} />
      </Route>
    </Routes>
  );
}

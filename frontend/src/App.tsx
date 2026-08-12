import { Routes, Route } from "react-router-dom";
import Landing from "@/pages/Landing";
import Generate from "@/pages/Generate";
import Workspace from "@/pages/Workspace";
import Library from "@/pages/Library";
import Corpus from "@/pages/Corpus";
import Dojo from "@/pages/Dojo";
import SiteHeader from "@/components/SiteHeader";

export default function App() {
  return (
    <div className="min-h-screen">
      <SiteHeader />
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/generate" element={<Generate />} />
        <Route path="/idea" element={<Workspace />} />
        <Route path="/library" element={<Library />} />
        <Route path="/corpus" element={<Corpus />} />
        <Route path="/dojo" element={<Dojo />} />
        <Route path="*" element={<Landing />} />
      </Routes>
    </div>
  );
}

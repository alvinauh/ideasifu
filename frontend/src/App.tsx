import { Routes, Route } from "react-router-dom";
import Landing from "@/pages/Landing";
import Start from "@/pages/Start";
import Workspace from "@/pages/Workspace";
import Library from "@/pages/Library";
import Corpus from "@/pages/Corpus";
import Dojo from "@/pages/Dojo";
import Community from "@/pages/Community";
import Formatter from "@/pages/Formatter";
import SiteHeader from "@/components/SiteHeader";

export default function App() {
  return (
    <div className="min-h-screen">
      <SiteHeader />
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/start" element={<Start />} />
        <Route path="/idea" element={<Workspace />} />
        <Route path="/library" element={<Library />} />
        <Route path="/corpus" element={<Corpus />} />
        <Route path="/dojo" element={<Dojo />} />
        <Route path="/community" element={<Community />} />
        <Route path="/format" element={<Formatter />} />
        <Route path="*" element={<Landing />} />
      </Routes>
    </div>
  );
}

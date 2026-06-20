import { useState } from "react";
import axios from "axios";

function App() {
  const [file, setFile] = useState(null);

  const handleUpload = async () => {
    if (!file) {
      alert("Select a PDF first");
      return;
    }

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await axios.post(
        "http://localhost:8000/upload",
        formData
      );

      console.log(res.data);
      alert("Upload Successful");
    } catch (err) {
      console.error(err);
      alert("Upload Failed");
    }
  };

  return (
    <div>
      <h1>PDF Upload</h1>

      <input
        type="file"
        accept=".pdf"
        onChange={(e) => setFile(e.target.files[0])}
      />

      <button onClick={handleUpload}>
        Upload
      </button>
    </div>
  );
}

export default App;
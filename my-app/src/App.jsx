
import React, { useEffect, useState } from 'react';
import './App.css';
import { io } from 'socket.io-client';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';

export default function App() {
  const [patientData, setPatientData] = useState(null);
  const [messages, setMessages] = useState([{ sender: 'bot', text: 'Hello' }]);
  const [docType, setDocType] = useState('');
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [showUploadPopup, setShowUploadPopup] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [inputMessage, setInputMessage] = useState('');

  useEffect(() => {
    const socket = io('http://localhost:5000', {
      transports: ['websocket'],
      reconnection: true,
      reconnectionAttempts: 5,
      reconnectionDelay: 2000,
    });

    socket.on('connect', () => {
      console.log('✅ Connected to Flask WebSocket server');
    });

    socket.on('disconnect', () => {
      console.log('🧹 WebSocket connection closed');
    });

    socket.on('message', (data) => {
      setMessages((prev) => {
        if (prev[prev.length - 1].text !== data.data) {
          return [...prev, { sender: 'bot', text: data.data }];
        }
        return prev;
      });
    });

    socket.on('patient_data', (data) => {
      setPatientData(data);
    });

    return () => {
      socket.disconnect();
    };
  }, []);

  const handleSendMessage = async () => {
    if (inputMessage.trim()) {
      setMessages((prev) => [...prev, { sender: 'user', text: inputMessage }]);
    }

    try {
      if (selectedFile) {
        setMessages((prev) => [
          ...prev,
          {
            sender: 'user',
            text: `📎 Uploaded: ${selectedFile.name} (${docType || 'Unknown Type'})`,
          },
        ]);

        const formData = new FormData();
        formData.append('file', selectedFile);
        formData.append('question', inputMessage || 'Please analyze this document.');
        formData.append('docType', docType); 

        const res = await axios.post('http://localhost:5000/ask-question', formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
        });

        const paragraphs = res.data.response.split(/\n\s*\n/);

        setMessages((prev) => [
          ...prev,
          ...paragraphs.map((para) => ({
            sender: 'bot',
            text: para.replace(/^[-*\d.]+\s*/, '').trim(),
          })),
        ]);

        setSelectedFile(null);
        setDocType('');
        setShowUploadPopup(false);
      } else if (inputMessage.trim()) {
        const res = await axios.post('http://localhost:5000/chat', {
          question: inputMessage,
        });

        setMessages((prev) => [
          ...prev,
          { sender: 'bot', text: res.data.response },
        ]);
      }
    } catch (err) {
      console.error('❌ Error sending message:', err);
      setMessages((prev) => [
        ...prev,
        { sender: 'bot', text: '❌ Something went wrong.' },
      ]);
    }

    setInputMessage('');
  };

  return (
    <div className="app">
      <div className={`sidebar ${sidebarOpen ? 'open' : 'collapsed'}`}>
        <button className="toggle-btn" onClick={() => setSidebarOpen(!sidebarOpen)}>
          {sidebarOpen ? '←' : '→'}
        </button>
        {sidebarOpen && (
          <ul>
            <div>🏠</div>
            <div>📁</div>
            <div>📊</div>
            <div>⚙️</div>
          </ul>
        )}
      </div>

      <div className="left-panel">
        <h2>🩺 HealthApp</h2><br />
        <h3>Patient Data</h3>
        <div className="data-box">
          {patientData ? (
            <>
              <div className="data-item"><p>🛌 Sleep: {patientData.sleep_hours}h</p></div>
              <div className="data-item"><p>❤️ HR: {patientData.heart_rate} bpm</p></div>
              <div className="data-item"><p>💉 BP: {patientData.bp_systolic}/{patientData.bp_diastolic} mmHg</p></div>
              <div className="data-item"><p>💓 Heart: {patientData.heart_rate} bpm</p></div>
            </>
          ) : (
            <p>⏳ Waiting for data...</p>
          )}
        </div>

        <h3>Upload History</h3>
        <ul className="history-list">
          <li>📄 bill.pdf <span>Just now</span></li>
          <li>📄 prescription.pdf <span>Yesterday</span></li>
          <li>📄 report.pdf <span>1 week ago</span></li>
        </ul>
      </div>

      <div className="right-panel">
        <h2>Chat</h2>
        <div className="chat-area">
          {messages.map((msg, i) => (
            <div key={i} className={msg.sender === 'user' ? 'user-msg' : 'bot-msg'}>
              <ReactMarkdown
                components={{
                  p: ({ node, ...props }) => <p style={{ margin: '8px 0' }} {...props} />,
                  li: ({ node, ...props }) => <p style={{ margin: '8px 0' }} {...props} />,
                }}
              >
                {msg.text.replace(/^[-*\d.]+\s*/gm, '')}
              </ReactMarkdown>
            </div>
          ))}
        </div>

        <div className="input-area">
          <div className="upload-dropdown-wrapper">
            <button className="plus-btn" onClick={() => setShowUploadPopup(!showUploadPopup)}>+</button>
            {showUploadPopup && (
              <div className="upload-popup">
                <label className="upload-label">
                  📎 Upload File
                  <input type="file" onChange={(e) => setSelectedFile(e.target.files[0])} />
                </label>
                <select className="doc-select" onChange={(e) => setDocType(e.target.value)} value={docType}>
                  <option value="">Select Type</option>
                  <option value="Bill">Bill</option>
                  <option value="Prescription">Prescription</option>
                  <option value="Photo">Photo</option>
                </select>
              </div>
            )}
          </div>

          <input
            type="text"
            placeholder="Type a message..."
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
          />

          {(inputMessage.trim() || selectedFile) ? (
            <button className="mic-btn" onClick={handleSendMessage}>📤</button>
          ) : (
            <button className="mic-btn">🎤</button>
          )}
        </div>
      </div>
    </div>
  );
}
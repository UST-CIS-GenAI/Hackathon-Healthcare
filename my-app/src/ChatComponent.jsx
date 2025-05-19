// ChatComponent.jsx

import React, { useState, useEffect } from "react";
import axios from "axios";
import ReactMarkdown from "react-markdown";

const ChatComponent = ({ messages, setMessages, inputMessage, setInputMessage, docType, setDocType, selectedFile, setSelectedFile, docTypeError, setDocTypeError, handleSendMessage, showUploadPopup, setShowUploadPopup }) => {
  const handleOptionClick = async option => {
    setMessages(prev => [...prev, { sender: "user", text: option }]);
    setInputMessage(option);
    await handleSendMessage(option, false);
  };

  return (
    <div className="right-panel">
      <h2>Chat</h2>
      <div className="chat-area">
        {messages.map((msg, i) => (
          <div key={i} className={msg.sender === "user" ? "user-msg" : "bot-msg"}>
            {msg.text.startsWith("📎 Uploaded:") ? (
              <div className="upload-chat-bubble">
                <div className="file-icon">📄</div>
                <div className="file-details">
                  <div className="file-name">{msg.text.split(":")[1].split("(")[0].trim()}</div>
                  <div className="file-type">{msg.text.match(/\((.*?)\)/)?.[1]}</div>
                </div>
              </div>
            ) : (
              <>
                <ReactMarkdown
                  components={{
                    p: ({ node, ...props }) => <p style={{ margin: "8px 0" }} {...props} />,
                    li: ({ node, ...props }) => <p style={{ margin: "8px 0" }} {...props} />
                  }}
                >
                  {msg.text.replace(/^[-*\d.]+\s*/gm, "")}
                </ReactMarkdown>

                {msg.options && (
                  <div className="option-buttons">
                    {msg.options.map((option, index) => (
                      <button key={index} className="option-btn" onClick={() => handleOptionClick(option)}>
                        {option}
                      </button>
                    ))}
                  </div>
                )}
              </>
            )}
          </div>
        ))}
      </div>

      <div className="input-area">
        <div className="upload-dropdown-wrapper">
          <button
            className="action-btn"
            onClick={() => {
              setDocType("Prescription");
              setShowUploadPopup(true);
            }}
          >
            Upload Prescription
          </button>

          <button
            className="action-btn"
            onClick={() => {
              setDocType("Bill");
              setShowUploadPopup(true);
            }}
          >
            Upload Bill
          </button>
        </div>

        {showUploadPopup && (
          <div className="upload-popup">
            <label className="upload-label">
              📎 Upload File
              <input
                type="file"
                onChange={e => {
                  setSelectedFile(e.target.files[0]);
                  setShowUploadPopup(false); // auto-close on selection
                }}
              />
            </label>
            <p style={{ fontSize: "0.85rem", marginTop: "4px" }}>
              Uploading for: <strong>{docType}</strong>
            </p>
          </div>
        )}

        <input type="text" autoComplete="off" placeholder="Type a message..." value={inputMessage} onChange={e => setInputMessage(e.target.value)} />

        {inputMessage.trim() || selectedFile ? (
          <button className="mic-btn" onClick={() => handleSendMessage()}>
            📤
          </button>
        ) : (
          <button className="mic-btn">🎤</button>
        )}
      </div>
    </div>
  );
};

export default ChatComponent;

import React, { useEffect, useRef, useState } from "react";
import "./App.css";
import { io } from "socket.io-client";
import axios from "axios";
import ReactMarkdown from "react-markdown";
import LeftPanel from "./leftpanel";
import Sidebar from "./sidebar"; // Add this at the top with other imports
import botIcon from "./assets/bot.png";
import userIcon from "./assets/user.png";
import { Send, Mic, Clock, FileText } from "lucide-react";

export default function App() {
  const [patientData, setPatientData] = useState(null);
  const [messages, setMessages] = useState([{ sender: "bot", text: "Hello" }]);
  const [docType, setDocType] = useState("");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [showUploadPopup, setShowUploadPopup] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [inputMessage, setInputMessage] = useState("");
  const [docTypeError, setDocTypeError] = useState("");
  const [appointmentMode, setAppointmentMode] = useState(false);
  const [appointmentAnswers, setAppointmentAnswers] = useState([]);
  const [refillReminders, setRefillReminders] = useState([]);
  const [showStores, setShowStores] = useState(false);
  const [refillMedicineName, setRefillMedicineName] = useState("");
  const [selectedStore, setSelectedStore] = useState(null);
  const [storeMedicines, setStoreMedicines] = useState([]);
  const [showPaymentForm, setShowPaymentForm] = useState(false);
  const [selectedMedicine, setSelectedMedicine] = useState(null);
  const [selectedLocation, setSelectedLocation] = useState("");
  const [isBotTyping, setIsBotTyping] = useState(false); // Loading state
  const uploadRef = useRef(null);
  const [storeMedicineData, setStoreMedicineData] = useState({});

  const [prescreeningMode, setPrescreeningMode] = useState(false);
  const [prescreeningAnswers, setPrescreeningAnswers] = useState([]);

  useEffect(() => {
    const fetchStores = async () => {
      try {
        const res = await axios.get("http://localhost:5000/stores");
        setStoreMedicineData(res.data);
      } catch (err) {
        console.error("❌ Failed to fetch store data:", err);
      }
    };

    fetchStores();
  }, []);

  useEffect(() => {
    const handleClickOutside = event => {
      if (uploadRef.current && !uploadRef.current.contains(event.target)) {
        setShowUploadPopup(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, []);

  useEffect(() => {
    const socket = io("http://localhost:5000", {
      transports: ["websocket"],
      reconnection: true,
      reconnectionAttempts: 5,
      reconnectionDelay: 2000
    });

    socket.on("connect", () => console.log("✅ Connected to Flask WebSocket server"));
    socket.on("disconnect", () => console.log("🧹 WebSocket connection closed"));
    socket.on("message", data => {
      setMessages(prev => {
        if (prev[prev.length - 1].text !== data.data) {
          return [...prev, { sender: "bot", text: data.data }];
        }
        return prev;
      });
    });
    socket.on("patient_data", data => setPatientData(data));

    return () => socket.disconnect();
  }, []);

  // ✅ Schedule reminder notifications
  const scheduleReminderNotifications = reminders => {
    if (!("Notification" in window)) return;

    Notification.requestPermission().then(permission => {
      if (permission !== "granted") return;

      reminders.forEach(reminder => {
        const time = new Date(reminder.datetime).getTime();
        const delay = time - Date.now();

        if (delay > 0) {
          setTimeout(() => {
            new Notification("💊 Medicine Reminder", {
              body: `Time to take ${reminder.medicine}`,
              icon: "/pill.png" // optional icon in public/
            });
          }, delay);
        }
      });
    });
  };
  const scheduleRefillNotifications = refillReminders => {
    if (!("Notification" in window)) return;

    refillReminders.forEach(reminder => {
      const time = new Date(reminder.refill_date).getTime();
      const delay = time - Date.now();

      if (delay > 0) {
        setTimeout(() => {
          new Notification("🛒 Refill Reminder", {
            body: `Time to refill ${reminder.medicine}`,
            icon: "/refill.png"
          });
        }, delay);
      }
    });
  };
  const handleStoreClick = storeName => {
    setSelectedStore(storeName);
    const store = storeMedicineData[storeName];
    const matchedMeds = store?.medicines.filter(med => med.name.toLowerCase() === refillMedicineName.toLowerCase()) || [];
    setStoreMedicines(matchedMeds);
  };

  const handleMedicineClick = medicine => {
    setSelectedMedicine(medicine);
    setShowPaymentForm(true);
  };

  const handleSendMessage = async (message = inputMessage, addUserMessage = true) => {
    setIsBotTyping(true);
    if (selectedFile && !docType) {
      setDocTypeError("⚠️ Please select a document type");
      return;
    } else {
      setDocTypeError("");
    }

    const isAppointmentRequest = /appointment/i.test(message);

    if (selectedFile) {
      setMessages(prev => [
        ...prev,
        {
          sender: "user",
          text: `📎 Uploaded: ${selectedFile.name} (${docType || "Unknown Type"})`
        }
      ]);

      const formData = new FormData();
      formData.append("file", selectedFile);
      formData.append("question", message || "Please analyze this document.");
      formData.append("docType", docType);

      let url = "http://localhost:5000/ask-question";
      if (docType === "Prescription") url = "http://localhost:5000/prescription";
      if (isAppointmentRequest) url = "http://localhost:5000/appointment";

      try {
        const res = await axios.post(url, formData, {
          headers: { "Content-Type": "multipart/form-data" }
        });

        if (docType === "Prescription" && res.data.data) {
          const meds = res.data.data;
          const reminders = res.data.scheduled_reminders;
          const refillReminders = res.data.refill_reminders || [];
          if (reminders?.length) {
            scheduleReminderNotifications(reminders);
          }

          if (refillReminders.length) {
            scheduleRefillNotifications(refillReminders);
          }

          const reminderText = meds
            .map(item => {
              return `*${item.medicine}*\n🕒 Time: ${item.time.join(", ")}\n🍽️ Meal: ${item.meal || "N/A"}\n📅 Days: ${item.days}`;
            })
            .join("\n\n");

          const refillText = refillReminders
            .map(item => {
              const refillTime = new Date(item.refill_date).toLocaleString();
              return `🛒 *${item.medicine}* refill reminder at ${refillTime}`;
            })
            .join("\n");

          const combinedText = `✅ Medicine reminders set:\n\n${reminderText}${refillText ? "\n\n" + refillText : ""}`;
          setMessages(prev => [
            ...prev,
            {
              sender: "bot",
              text: combinedText
            }
          ]);
        } else {
          const paragraphs = res.data.response.split(/\n\s*\n/);
          setMessages(prev => [
            ...prev,
            ...paragraphs.map(para => ({
              sender: "bot",
              text: para.replace(/^[-*\d.]+\s*/, "").trim()
            }))
          ]);
        }

        setSelectedFile(null);
        setDocType("");
        setShowUploadPopup(false);
      } catch (err) {
        console.error("❌ Error:", err);
        setMessages(prev => [...prev, { sender: "bot", text: "❌ Upload failed." }]);
      }
    } else if (message.trim()) {
      if (addUserMessage) {
        setMessages(prev => [...prev, { sender: "user", text: message }]);
      }

      let res;

      try {
        if (isAppointmentRequest && !appointmentMode) {
          setAppointmentMode(true);
          setAppointmentAnswers([]);
          res = await axios.post("http://localhost:5000/appointment", { answers: [] });
        } else if (appointmentMode) {
          const updatedAnswers = [...appointmentAnswers, message];
          setAppointmentAnswers(updatedAnswers);
          res = await axios.post("http://localhost:5000/appointment", { answers: updatedAnswers });

          if (res.data.response.includes("Appointment confirmed")) {
            setAppointmentMode(false);
            setAppointmentAnswers([]);
          }
        } else if (/prescreen/i.test(message) && !prescreeningMode) {
          setPrescreeningMode(true);
          setPrescreeningAnswers([]);
          res = await axios.post("http://localhost:5000/prescreening", { answers: [] });
        } else if (prescreeningMode) {
          const updatedAnswers = [...prescreeningAnswers, message];
          setPrescreeningAnswers(updatedAnswers);
          res = await axios.post("http://localhost:5000/prescreening", { answers: updatedAnswers });

          if (res.data.response.includes("Prescreening completed") && res.data.file_url) {
            setMessages(prev => [
              ...prev,
              {
                sender: "bot",
                text: `Prescreening completed. [📄 Click here to download PDF](${res.data.file_url})`
              }
            ]);
            setPrescreeningMode(false); // ✅ Exit prescreening mode
            return;
          }
        } else {
          res = await axios.post("http://localhost:5000/chat", { question: message });
        }

        setMessages(prev => [
          ...prev,
          {
            sender: "bot",
            text: res.data.response,
            options: res.data.options || null
          }
        ]);
      } catch (err) {
        console.error("❌ Error:", err);
        setMessages(prev => [...prev, { sender: "bot", text: "❌ Something went wrong." }]);
      } finally {
        setIsBotTyping(false); // Hide typing dots animation after response
      }
    }
    setIsBotTyping(false);
    setInputMessage("");
  };

  const handleOptionClick = async option => {
    setMessages(prev => [...prev, { sender: "user", text: option }]);
    setInputMessage(option);
    await handleSendMessage(option, false);
  };

  return (
    <div className="app">
      <Sidebar sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />

      <LeftPanel patientData={patientData} refillReminders={refillReminders} showStores={showStores} setShowStores={setShowStores} refillMedicineName={refillMedicineName} setRefillMedicineName={setRefillMedicineName} setSelectedLocation={setSelectedLocation} storeMedicineData={storeMedicineData} selectedStore={selectedStore} setSelectedStore={setSelectedStore} handleStoreClick={handleStoreClick} storeMedicines={storeMedicines} showPaymentForm={showPaymentForm} selectedMedicine={selectedMedicine} setShowPaymentForm={setShowPaymentForm} selectedLocation={selectedLocation} handleMedicineClick={handleMedicineClick} />

      <div className="right-panel">
        <div className="header-bar">
          <h2>Medchat</h2>

          <div className="prescreen-buttons">
            <button className="prescreen-btn" onClick={() => handleSendMessage("prescreening")}>
              Start Prescreening
            </button>

            <button
              className="prescreen-btn"
              onClick={() => {
                setDocType("Bill");
                setShowUploadPopup(true);
              }}
            >
              Upload Bill
            </button>
          </div>
        </div>

        <div className="chat-area">
          {messages.map((msg, i) => (
            <div key={i} className={msg.sender === "user" ? "user-msg" : "bot-msg"}>
              <div className="chat-line">
                <div className="chat-icon">
                  <img src={msg.sender === "user" ? userIcon : botIcon} alt="icon" />
                </div>
                <div className="chat-bubble">
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
                        {msg.text.replace(/^\s*[-*]\s+/gm, "")}
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
              </div>
            </div>
          ))}

          {/* Loading Indicator (Dot Animation) */}
          {isBotTyping && (
            <div className="bot-msg">
              <div className="chat-line">
                <div className="chat-icon">
                  <img src={botIcon} alt="bot typing" />
                </div>
                <div className="chat-bubble">
                  <div className="typing-indicator">
                    <span></span>
                    <span></span>
                    <span></span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        <div className="input-area">
          <p
            onClick={() => {
              setDocType("Prescription"); // Set hidden value
              setShowUploadPopup(true); // Show popup
            }}
            className="tooltip-container" // Add a class for the tooltip container
            style={{ cursor: "pointer" }}
          >
            <Clock size={25} color="#FF5722" />
            <span className="tooltip-text">Set Medical Reminder</span> {/* Custom Tooltip */}
          </p>

          <input
            type="text"
            placeholder="Type a message..."
            value={inputMessage}
            onChange={e => setInputMessage(e.target.value)}
            onKeyDown={e => {
              if (e.key === "Enter" && inputMessage.trim()) {
                e.preventDefault(); // Prevent the Enter key from adding a new line
                handleSendMessage(); // Call the send message function
              }
            }}
          />

          {/* Show file name when a file is selected */}
          {selectedFile && (
            <div className="file-uploaded-message" style={{ marginTop: "10px", fontSize: "0.9rem", color: "#555" }}>
              <FileText size={15} color="#FF5722" /> Selected
            </div>
          )}

          {inputMessage.trim() || selectedFile ? (
            <button className="mic-btn" onClick={() => handleSendMessage()}>
              <Send size={20} color="#fff" />{" "}
            </button>
          ) : (
            <button className="mic-btn">
              {" "}
              <Mic size={20} color="#fff" />{" "}
            </button>
          )}
          {showUploadPopup && (
            <div className="upload-popup" ref={uploadRef}>
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
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

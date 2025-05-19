import React, { useState, useEffect } from "react";
import "./leftpanel.css";
import logo from "./assets/logo.png";
import { Heart, BedDouble, Droplet, FileText, Bell, DollarSign } from "lucide-react";
import medstock from "./assets/medstock.jpeg"; // Adjust the path based on where your logo is stored

export default function LeftPanel({ patientData, refillReminders, showStores, setShowStores, refillMedicineName, setRefillMedicineName, setSelectedLocation, storeMedicineData, selectedStore, setSelectedStore, handleStoreClick, storeMedicines, showPaymentForm, selectedMedicine, setShowPaymentForm, selectedLocation, handleMedicineClick }) {
  // State for liquid fill values
  const [heartRateFill, setHeartRateFill] = useState(0);
  const [sleepFill, setSleepFill] = useState(0);
  const [bpSystolicFill, setBpSystolicFill] = useState(0);
  const [bpDiastolicFill, setBpDiastolicFill] = useState(0);

  useEffect(() => {
    if (patientData) {
      // Match backend-generated ranges:
      const heartRatePercent = ((patientData.heart_rate - 60) / (120 - 60)) * 100;
      const sleepPercent = ((patientData.sleep_hours - 4) / (9 - 4)) * 100;
      const bpSystolicPercent = ((patientData.bp_systolic - 100) / (140 - 100)) * 100;
      const bpDiastolicPercent = ((patientData.bp_diastolic - 60) / (90 - 60)) * 100;

      setHeartRateFill(heartRatePercent);
      setSleepFill(sleepPercent);
      setBpSystolicFill(bpSystolicPercent);
      setBpDiastolicFill(bpDiastolicPercent);
    }
  }, [patientData]);

  return (
    <div className="left-panel">
      {!showStores ? (
        <>
          <div className="app-header">
            <img src={logo} alt="HealthApp Logo" className="logo" />
            <h1>HealthApp</h1>
          </div>
          <br />

          <h3>Patient Data</h3>
          <div className="data-box">
            {patientData ? (
              <>
                {/* Heart Rate */}
                <div className="data-item">
                  <div
                    className="fill"
                    style={{
                      height: `${heartRateFill}%`,
                      backgroundColor: `hsl(${120 - heartRateFill * 1.2}, 100%, 50%)` // Green to red
                    }}
                  ></div>

                  <p className="value-text">
                    <Heart className="icon-heart" size={15} style={{ marginRight: "5px" }} /> HR: {patientData.heart_rate} bpm
                  </p>
                </div>

                {/* Sleep */}
                <div className="data-item">
                  <div
                    className="fill"
                    style={{
                      height: `${sleepFill}%`,
                      backgroundColor: `hsl(${sleepFill * 1.2}, 100%, 50%)` // Less sleep = redder
                    }}
                  ></div>

                  <p className="value-text">
                    <BedDouble size={18} color="#3b82f6" style={{ marginRight: "6px" }} />
                    Sleep: {patientData.sleep_hours}h
                  </p>
                </div>

                {/* BP Systolic */}
                <div className="data-item">
                  <div
                    className="fill"
                    style={{
                      height: `${bpSystolicFill}%`,
                      backgroundColor: `hsl(${120 - bpSystolicFill * 1.2}, 100%, 50%)`
                    }}
                  ></div>

                  <p className="value-text">
                    <Droplet size={18} color="#e63946" style={{ marginRight: "6px" }} />
                    SBP: {patientData.bp_systolic}hg
                  </p>
                </div>

                {/* Heart Rate (again for consistency) */}
                <div className="data-item">
                  <div
                    className="fill"
                    style={{
                      height: `${bpDiastolicFill}%`,
                      backgroundColor: `hsl(${120 - bpDiastolicFill * 1.2}, 100%, 50%)`
                    }}
                  ></div>

                  <p className="value-text">
                    {" "}
                    <Droplet size={18} color="#e63946" style={{ marginRight: "6px" }} />
                    DBP: {patientData.bp_diastolic} hg
                  </p>
                </div>
              </>
            ) : (
              <p>⏳ Waiting for data...</p>
            )}
          </div>

          <h3>Prescreening Reports</h3>
          <ul className="history-list">
            {/* Replace the file icon with a new one */}
            <li>
              <FileText size={18} color="#3498db" style={{ marginRight: "1px" }} /> Pre_Report_1_250511.pdf <span>Just now</span>
            </li>
            {/* <li><FileText size={18} color="#3498db" style={{ marginRight: '1px' }} /> Pre_Report_2_250511.pdf<span>Yesterday</span></li>
            <li><FileText size={18} color="#3498db" style={{ marginRight: '1px' }} /> Pre_Report_3_250511.pdf<span>1 week ago</span></li> */}
          </ul>

          <h3>Refill Reminders</h3>
          <ul className="history-list">
            <li style={{ display: "flex", flexDirection: "column", alignItems: "flex-start" }}>
              <div>
                <Bell size={18} color="#FACC15" style={{ marginRight: "6px" }} /> <strong>Metformin</strong> <span>May 16, 2025, 10:00 AM</span>
              </div>
              <a
                href="#"
                onClick={e => {
                  e.preventDefault();
                  setRefillMedicineName("Metformin");
                  setShowStores(true);
                }}
                style={{
                  fontSize: "0.85rem",
                  color: "#007bff",
                  marginTop: "4px",
                  textDecoration: "underline"
                }}
              >
                Refill this medicine
              </a>
            </li>
          </ul>
        </>
      ) : (
        <div className="store-list">
          <h3 className="store-title">
            <img src={medstock} alt="Logo" className="store-logo" />
            Stores
          </h3>

          {/* Location Dropdown */}
          <label className="location-dropdown">
            Filter by location:{" "}
            <select onChange={e => setSelectedLocation(e.target.value)} value={selectedLocation}>
              <option value="">Select a place</option>
              <option value="Downtown">Downtown</option>
              <option value="Suburb">Suburb</option>
              <option value="Uptown">Uptown</option>
            </select>
          </label>

          {/* Store Cards Filtered by Location */}
          <div className="store-cards-container">
            {Object.entries(storeMedicineData)
              .filter(([storeName, storeData]) => storeData.medicines.some(med => med.name.toLowerCase() === refillMedicineName.toLowerCase()))
              .filter(([_, storeData]) => !selectedLocation || storeData.location === selectedLocation)
              .map(([storeName]) => (
                <div key={storeName} className={`store-card ${selectedStore === storeName ? "selected" : ""}`} onClick={() => handleStoreClick(storeName)}>
                  <strong>{storeName}</strong>
                  <p>Tap to view medicines</p>
                </div>
              ))}
          </div>

          {/* Medicine List for Selected Store */}
          {selectedStore && storeMedicines.length > 0 && (
            <div className="medicine-list">
              <h4> Available at {selectedStore}:</h4>
              <ul>
                {storeMedicines.map((med, index) => (
                  <li key={index} className="medicine-item">
                    <div className="medicine-details">
                      <strong>{med.name}</strong>
                      <p>{med.description}</p>
                      <span className="medicine-price">
                        {" "}
                        <DollarSign size={16} color="#28a745" style={{ marginRight: "5px" }} /> {med.price}
                      </span>
                    </div>
                    <button onClick={() => handleMedicineClick(med)} className="buy-btn">
                      Buy Now
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Payment Form */}
          {showPaymentForm && selectedMedicine && (
            <div className="payment-form">
              <h3>Payment for {selectedMedicine.name}</h3>
              <p>
                {" "}
                <DollarSign size={16} color="#28a745" style={{ marginRight: "5px" }} /> Price: {selectedMedicine.price}
              </p>
              <p>📄 {selectedMedicine.description}</p>
              <form>
                <label>
                  Name:
                  <input type="text" placeholder="Your Name" required />
                </label>
                <label>
                  Card Number:
                  <input type="text" placeholder="Card Number" required />
                </label>
                <label>
                  Expiration Date:
                  <input type="month" required />
                </label>
                <button type="submit" className="pay-now-btn">
                  Pay Now
                </button>
              </form>
              <button onClick={() => setShowPaymentForm(false)} className="cancel-btn">
                Cancel
              </button>
            </div>
          )}

          <button onClick={() => setShowStores(false)} className="back-btn">
            ← Back
          </button>
        </div>
      )}
    </div>
  );
}

import React from 'react';
import { Home, Folder,Settings,ShoppingCart } from 'lucide-react'; // Import Lucide icons


export default function Sidebar({ sidebarOpen, setSidebarOpen }) {
  return (
    <div className={`sidebar ${sidebarOpen ? 'open' : 'collapsed'}`}>
      <button className="toggle-btn" onClick={() => setSidebarOpen(!sidebarOpen)}>
        {sidebarOpen ? '←' : '→'}
      </button>
      {sidebarOpen && (
        <ul>
          <li><Home size={24} /> Home</li> {/* Home icon */}
          <li><Folder size={24} /> Files</li> {/* Folder icon */}
          <li><ShoppingCart size={24} />Store</li> {/* Shopping Cart icon */}
          <li><Settings size={24} /> Settings</li> {/* Settings icon */}
        </ul>
      )}
    </div>
  );
}

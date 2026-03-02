import { useEffect, useMemo, useState } from "react";
import ContactDetail from "./components/ContactDetail";
import ContactFormModal from "./components/ContactFormModal";
import ContactList from "./components/ContactList";
import { createContact, deleteContact, getContacts, updateContact } from "./api";

function mapApiError(error) {
  if (error?.details?.length) {
    return `${error.message}: ${error.details
      .map((detail) => `${detail.field} ${detail.message}`)
      .join(", ")}`;
  }
  return error?.message || "Unexpected error";
}

export default function App() {
  const [contacts, setContacts] = useState([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedContactId, setSelectedContactId] = useState(null);
  const [isPhoneLayout, setIsPhoneLayout] = useState(() => {
    if (typeof window === "undefined") {
      return false;
    }
    return window.matchMedia("(max-width: 767px)").matches;
  });
  const [isMobileDetailOpen, setIsMobileDetailOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [modalMode, setModalMode] = useState("create");
  const [editingContact, setEditingContact] = useState(null);
  const [errorMessage, setErrorMessage] = useState("");

  const selectedContact = useMemo(
    () => contacts.find((item) => item._id === selectedContactId) || null,
    [contacts, selectedContactId]
  );

  const loadContacts = async (query = "") => {
    setIsLoading(true);
    setErrorMessage("");
    try {
      const data = await getContacts(query);
      setContacts(data);
      if (!selectedContactId && data.length > 0) {
        setSelectedContactId(data[0]._id);
      }
      if (selectedContactId && !data.find((item) => item._id === selectedContactId)) {
        setSelectedContactId(data[0]?._id || null);
      }
    } catch (error) {
      setErrorMessage(mapApiError(error));
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadContacts();
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") {
      return undefined;
    }

    const mediaQuery = window.matchMedia("(max-width: 767px)");
    const handleChange = (event) => {
      setIsPhoneLayout(event.matches);
      if (!event.matches) {
        setIsMobileDetailOpen(false);
      }
    };

    setIsPhoneLayout(mediaQuery.matches);
    mediaQuery.addEventListener("change", handleChange);

    return () => mediaQuery.removeEventListener("change", handleChange);
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => {
      loadContacts(searchQuery);
    }, 250);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  useEffect(() => {
    if (!selectedContact) {
      setIsMobileDetailOpen(false);
    }
  }, [selectedContact]);

  const openCreateModal = () => {
    setModalMode("create");
    setEditingContact(null);
    setIsModalOpen(true);
  };

  const openEditModal = (contact) => {
    setModalMode("edit");
    setEditingContact(contact);
    setIsModalOpen(true);
  };

  const handleSubmitContact = async (payload) => {
    setIsSaving(true);
    setErrorMessage("");
    try {
      if (modalMode === "edit" && editingContact?._id) {
        await updateContact(editingContact._id, payload);
      } else {
        await createContact(payload);
      }
      setIsModalOpen(false);
      await loadContacts(searchQuery);
    } catch (error) {
      setErrorMessage(mapApiError(error));
    } finally {
      setIsSaving(false);
    }
  };

  const handleDeleteSelected = async () => {
    if (!selectedContact?._id) {
      return;
    }

    const shouldDelete = window.confirm("Delete this contact?");
    if (!shouldDelete) {
      return;
    }

    setErrorMessage("");
    try {
      await deleteContact(selectedContact._id);
      await loadContacts(searchQuery);
    } catch (error) {
      setErrorMessage(mapApiError(error));
    }
  };

  const handleSelectContact = (contact) => {
    if (!contact?._id) {
      return;
    }

    if (isPhoneLayout && selectedContactId === contact._id) {
      setIsMobileDetailOpen(true);
      return;
    }

    setSelectedContactId(contact._id);
    setIsMobileDetailOpen(false);
  };

  return (
    <main className={`app-shell ${isPhoneLayout ? "phone-layout" : ""}`}>
      <div className="app-frame">
        <ContactList
          contacts={contacts}
          selectedContactId={selectedContactId}
          onSelect={handleSelectContact}
          onCreate={openCreateModal}
        />

        <section className="right-pane">
          <div className="right-pane-toolbar">
            <input
              className="search-input"
              placeholder="Search contacts"
              value={searchQuery}
              onChange={(event) => setSearchQuery(event.target.value)}
            />
            <button className="ghost-button" onClick={() => loadContacts(searchQuery)}>
              Refresh
            </button>
            <button className="danger-button" onClick={handleDeleteSelected} disabled={!selectedContact}>
              Delete
            </button>
          </div>

          {errorMessage && <div className="error-banner">{errorMessage}</div>}
          {isLoading ? (
            <div className="loading-state">Loading contacts...</div>
          ) : (
            <ContactDetail contact={selectedContact} onEdit={openEditModal} compact={isPhoneLayout} />
          )}
        </section>
      </div>

      {isPhoneLayout && isMobileDetailOpen && selectedContact && (
        <section className="mobile-detail-screen" aria-label="Contact full details">
          <header className="mobile-detail-header">
            <button className="panel-link" onClick={() => setIsMobileDetailOpen(false)}>
              Back
            </button>
            <span className="mobile-detail-title">Full Details</span>
            <button className="panel-link" onClick={() => openEditModal(selectedContact)}>
              Edit
            </button>
          </header>
          <div className="mobile-detail-body">
            <ContactDetail contact={selectedContact} onEdit={openEditModal} />
          </div>
        </section>
      )}

      <ContactFormModal
        isOpen={isModalOpen}
        mode={modalMode}
        contact={editingContact}
        onClose={() => setIsModalOpen(false)}
        onSubmit={handleSubmitContact}
        isSaving={isSaving}
      />
    </main>
  );
}

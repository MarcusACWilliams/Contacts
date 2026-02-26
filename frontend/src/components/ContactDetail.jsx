function formatName(contact) {
  if (!contact) {
    return "Select a contact";
  }
  return `${contact.first || ""} ${contact.last || ""}`.trim() || "Unnamed Contact";
}

function renderAddress(address) {
  if (!address) {
    return "No address on file";
  }
  return address;
}

export default function ContactDetail({ contact, onEdit }) {
  if (!contact) {
    return (
      <section className="detail-panel empty">
        <p>Select a contact from the list to view details.</p>
      </section>
    );
  }

  const firstEmail = contact.emails?.[0]?.address || "";
  const firstPhone = contact.phone?.[0] || "";

  return (
    <section className="detail-panel">
      <header className="detail-header">
        <button className="panel-link">Contacts</button>
        <button className="panel-link" onClick={() => onEdit(contact)}>
          Edit
        </button>
      </header>

      <div className="profile-card">
        <div className="profile-avatar-lg">{(contact.first || "?").charAt(0).toUpperCase()}</div>
        <h2>{formatName(contact)}</h2>
        <p>{contact.company || "Personal Contact"}</p>
      </div>

      <div className="action-grid">
        <a className="action-chip" href={firstPhone ? `sms:${firstPhone}` : "#"}>
          Message
        </a>
        <a className="action-chip" href={firstEmail ? `mailto:${firstEmail}` : "#"}>
          Email
        </a>
        <a className="action-chip" href={firstPhone ? `tel:${firstPhone}` : "#"}>
          Call
        </a>
        <button className="action-chip" onClick={() => onEdit(contact)}>
          Edit
        </button>
      </div>

      <div className="detail-block">
        <label>Mobile</label>
        <div>{firstPhone || "No phone on file"}</div>
      </div>

      <div className="detail-block">
        <label>Email</label>
        <div>{firstEmail || "No email on file"}</div>
      </div>

      <div className="detail-block">
        <label>Address</label>
        <div>{renderAddress(contact.address)}</div>
      </div>

      <div className="notes-block">
        {contact.notes || "Add notes in the next iteration when we refine this screen."}
      </div>
    </section>
  );
}

function fullName(contact) {
  return `${contact.first || ""} ${contact.last || ""}`.trim();
}

function buildSections(contacts) {
  const sections = new Map();
  const sorted = [...contacts].sort((a, b) =>
    fullName(a).localeCompare(fullName(b), undefined, { sensitivity: "base" })
  );

  sorted.forEach((contact) => {
    const name = fullName(contact);
    const key = name?.[0]?.toUpperCase() || "#";
    const sectionKey = /[A-Z]/.test(key) ? key : "#";
    if (!sections.has(sectionKey)) {
      sections.set(sectionKey, []);
    }
    sections.get(sectionKey).push(contact);
  });

  return [...sections.entries()];
}

export default function ContactList({ contacts, selectedContactId, onSelect, onCreate }) {
  const sections = buildSections(contacts);

  return (
    <aside className="contacts-panel">
      <div className="panel-header">
        <span className="panel-link">All Contacts</span>
        <button className="circle-button" onClick={onCreate} aria-label="Create contact">
          +
        </button>
      </div>
      <h1 className="panel-title">Contacts</h1>

      <div className="search-decoration">Search by first or last name</div>

      <div className="contacts-sections">
        {sections.length === 0 && (
          <p className="empty-state">No contacts found. Add one to get started.</p>
        )}

        {sections.map(([letter, sectionContacts]) => (
          <section key={letter} className="contact-section">
            <h2>{letter}</h2>
            <ul>
              {sectionContacts.map((contact) => {
                const isSelected = selectedContactId === contact._id;
                return (
                  <li key={contact._id || fullName(contact)}>
                    <button
                      className={`contact-row ${isSelected ? "selected" : ""}`}
                      onClick={() => onSelect(contact)}
                    >
                      <span className="avatar-pill">{(contact.first || "?").charAt(0).toUpperCase()}</span>
                      <span className="row-main">
                        <strong>{fullName(contact) || "Unnamed Contact"}</strong>
                        <small>{contact.company || "Contact"}</small>
                      </span>
                    </button>
                  </li>
                );
              })}
            </ul>
          </section>
        ))}
      </div>
    </aside>
  );
}

import { useEffect, useMemo, useState } from "react";

const EMPTY_FORM = {
  first: "",
  last: "",
  address: "",
  phone: [""],
  emails: [{ address: "", type: "home" }]
};

function toFormState(contact) {
  if (!contact) {
    return EMPTY_FORM;
  }

  return {
    first: contact.first || "",
    last: contact.last || "",
    address: contact.address || "",
    phone: contact.phone?.length ? [...contact.phone] : [""],
    emails: contact.emails?.length
      ? contact.emails.map((email) => ({
          _id: email._id,
          _contact_id: email._contact_id,
          address: email.address || "",
          type: email.type || "home"
        }))
      : [{ address: "", type: "home" }]
  };
}

export default function ContactFormModal({ isOpen, mode, contact, onClose, onSubmit, isSaving }) {
  const [form, setForm] = useState(EMPTY_FORM);

  useEffect(() => {
    if (isOpen) {
      setForm(toFormState(contact));
    }
  }, [isOpen, contact]);

  const title = useMemo(() => (mode === "edit" ? "Edit Contact" : "New Contact"), [mode]);

  if (!isOpen) {
    return null;
  }

  const updateField = (field, value) => {
    setForm((previous) => ({ ...previous, [field]: value }));
  };

  const updateListItem = (field, index, value) => {
    setForm((previous) => {
      const next = [...previous[field]];
      next[index] = value;
      return { ...previous, [field]: next };
    });
  };

  const updateEmailItem = (index, key, value) => {
    setForm((previous) => {
      const next = [...previous.emails];
      next[index] = { ...next[index], [key]: value };
      return { ...previous, emails: next };
    });
  };

  const addPhone = () => {
    setForm((previous) => ({ ...previous, phone: [...previous.phone, ""] }));
  };

  const addEmail = () => {
    setForm((previous) => ({
      ...previous,
      emails: [...previous.emails, { address: "", type: "home" }]
    }));
  };

  const removePhone = (index) => {
    setForm((previous) => {
      const next = previous.phone.filter((_, itemIndex) => itemIndex !== index);
      return { ...previous, phone: next.length ? next : [""] };
    });
  };

  const removeEmail = (index) => {
    setForm((previous) => {
      const next = previous.emails.filter((_, itemIndex) => itemIndex !== index);
      return {
        ...previous,
        emails: next.length ? next : [{ address: "", type: "home" }]
      };
    });
  };

  const handleSubmit = (event) => {
    event.preventDefault();

    const payload = {
      first: form.first,
      last: form.last,
      address: form.address,
      phone: form.phone.map((item) => item.trim()).filter(Boolean),
      emails: form.emails
        .map((item) => ({
          ...item,
          address: item.address.trim()
        }))
        .filter((item) => item.address)
    };

    onSubmit(payload);
  };

  return (
    <div className="modal-overlay" role="presentation" onClick={onClose}>
      <div className="modal-card" role="dialog" aria-modal="true" onClick={(event) => event.stopPropagation()}>
        <div className="modal-header">
          <h3>{title}</h3>
          <button type="button" className="panel-link" onClick={onClose}>
            Close
          </button>
        </div>

        <form className="modal-body" onSubmit={handleSubmit}>
          <label>
            First Name
            <input
              value={form.first}
              onChange={(event) => updateField("first", event.target.value)}
              required
            />
          </label>

          <label>
            Last Name
            <input
              value={form.last}
              onChange={(event) => updateField("last", event.target.value)}
              required
            />
          </label>

          <label>
            Address
            <input
              value={form.address}
              onChange={(event) => updateField("address", event.target.value)}
            />
          </label>

          <div className="list-editor">
            <div className="list-header">
              <span>Phone</span>
              <button type="button" onClick={addPhone}>
                Add
              </button>
            </div>
            {form.phone.map((value, index) => (
              <div className="row-field" key={`phone-${index}`}>
                <input
                  value={value}
                  onChange={(event) => updateListItem("phone", index, event.target.value)}
                  placeholder="(555) 555-5555"
                />
                <button type="button" onClick={() => removePhone(index)}>
                  Remove
                </button>
              </div>
            ))}
          </div>

          <div className="list-editor">
            <div className="list-header">
              <span>Email</span>
              <button type="button" onClick={addEmail}>
                Add
              </button>
            </div>
            {form.emails.map((email, index) => (
              <div className="row-field" key={`email-${index}`}>
                <input
                  value={email.address}
                  onChange={(event) => updateEmailItem(index, "address", event.target.value)}
                  placeholder="name@example.com"
                />
                <button type="button" onClick={() => removeEmail(index)}>
                  Remove
                </button>
              </div>
            ))}
          </div>

          <button className="submit-button" type="submit" disabled={isSaving}>
            {isSaving ? "Saving..." : "Save Contact"}
          </button>
        </form>
      </div>
    </div>
  );
}

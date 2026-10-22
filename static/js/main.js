/* AI Email Generator - small vanilla JavaScript helpers */
document.addEventListener("DOMContentLoaded", function () {
  // ---------- mobile sidebar ----------
  var menuToggle = document.getElementById("menuToggle");
  var sidebar = document.getElementById("sidebar");
  if (menuToggle && sidebar) {
    menuToggle.addEventListener("click", function () { sidebar.classList.toggle("open"); });
  }

  // ---------- confirm before delete ----------
  document.querySelectorAll("form[data-confirm]").forEach(function (form) {
    form.addEventListener("submit", function (event) {
      if (!window.confirm(form.dataset.confirm)) { event.preventDefault(); }
    });
  });

  // ---------- copy to clipboard ----------
  function copyText(text, button) {
    function done() {
      var original = button.textContent;
      button.textContent = "Copied!";
      setTimeout(function () { button.textContent = original; }, 1500);
    }
    if (navigator.clipboard && window.isSecureContext) {
      navigator.clipboard.writeText(text).then(done, function () { fallbackCopy(text); done(); });
    } else {
      fallbackCopy(text);
      done();
    }
  }
  function fallbackCopy(text) {
    var area = document.createElement("textarea");
    area.value = text;
    area.style.position = "fixed";
    area.style.opacity = "0";
    document.body.appendChild(area);
    area.select();
    try { document.execCommand("copy"); } catch (e) { /* ignore */ }
    document.body.removeChild(area);
  }
  document.querySelectorAll("[data-copy-target]").forEach(function (button) {
    button.addEventListener("click", function () {
      var target = document.querySelector(button.dataset.copyTarget);
      if (target) { copyText(target.value, button); }
    });
  });
  document.querySelectorAll("[data-copy-body]").forEach(function (button) {
    button.addEventListener("click", function () {
      copyText("Subject: " + button.dataset.copySubject + "\n\n" + button.dataset.copyBody, button);
    });
  });

  // ---------- generate form ----------
  var purpose = document.getElementById("id_purpose");
  var customGroup = document.getElementById("customPurposeGroup");
  if (purpose && customGroup) {
    var toggleCustom = function () { customGroup.hidden = purpose.value !== "Custom"; };
    purpose.addEventListener("change", toggleCustom);
    toggleCustom();
  }
  var generateForm = document.getElementById("generateForm");
  if (generateForm) {
    generateForm.addEventListener("submit", function () {
      var button = document.getElementById("generateBtn");
      button.disabled = true;
      button.textContent = "Generating...";
      document.getElementById("generateHint").hidden = false;
    });
  }

  // ---------- AI actions on the editor ----------
  var editor = document.getElementById("emailEditor");
  if (editor) {
    var subjectField = document.getElementById("id_subject");
    var bodyField = document.getElementById("id_body");
    var status = document.getElementById("aiStatus");
    var unsaved = document.getElementById("unsavedHint");
    var csrf = document.querySelector("#editorForm input[name=csrfmiddlewaretoken]").value;
    var aiButtons = editor.querySelectorAll("[data-ai-action]");

    function showStatus(type, text) {
      status.className = "alert alert-" + type;
      status.textContent = text;
      status.hidden = false;
    }
    function markUnsaved() { unsaved.hidden = false; }
    subjectField.addEventListener("input", markUnsaved);
    bodyField.addEventListener("input", markUnsaved);

    aiButtons.forEach(function (button) {
      button.addEventListener("click", function () {
        var action = button.dataset.aiAction;
        aiButtons.forEach(function (b) { b.disabled = true; });
        showStatus("loading", "The AI is working on your email...");

        fetch(editor.dataset.aiUrl, {
          method: "POST",
          headers: { "Content-Type": "application/json", "X-CSRFToken": csrf },
          body: JSON.stringify({ action: action, subject: subjectField.value, body: bodyField.value })
        })
          .then(function (response) {
            return response.json().then(
              function (data) { return { ok: response.ok, data: data }; },
              function () { throw new Error("Your session may have expired. Please refresh the page and log in again."); }
            );
          })
          .then(function (result) {
            if (!result.ok) { throw new Error(result.data.error || "Something went wrong. Please try again."); }
            subjectField.value = result.data.subject;
            bodyField.value = result.data.body;
            markUnsaved();
            showStatus("success", "Done! Review the new version and press Save Email to keep it.");
          })
          .catch(function (error) {
            showStatus("danger", error.message || "Could not contact the server. Please try again.");
          })
          .finally(function () {
            aiButtons.forEach(function (b) { b.disabled = false; });
          });
      });
    });
  }
});

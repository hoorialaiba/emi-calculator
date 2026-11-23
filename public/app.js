$(function () {
  const fmt = (x) => Number(x).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

  function validate() {
    let ok = true;
    const rules = {
      P: (v) => v > 0 || 'Enter a loan amount greater than 0',
      rate: (v) => v > 0 || 'Enter an interest rate greater than 0',
      n: (v) => (v > 0 && Number.isInteger(v)) || 'Enter a whole number of months, 1 or more',
    };
    Object.keys(rules).forEach((id) => {
      const $el = $('#' + id);
      const raw = $el.val().trim();
      const res = raw === '' ? 'This field is required' : rules[id](Number(raw));
      if (res !== true) { $el.addClass('is-invalid').next('.invalid-feedback').text(res); ok = false; }
      else { $el.removeClass('is-invalid'); }
    });
    return ok;
  }

  function loadHistory() {
    $.getJSON('/api/history').done(function (rows) {
      const $body = $('#historyBody').empty();
      if (!rows.length) {
        $body.append('<tr><td colspan="6" class="text-muted">No calculations yet.</td></tr>');
        return;
      }
      rows.forEach(function (r) {
        const $tr = $('<tr>');
        $tr.append($('<td>').text(new Date(r.createdAt).toLocaleString()));
        $tr.append($('<td>').text(fmt(r.principal)));
        $tr.append($('<td>').text(r.rate));
        $tr.append($('<td>').text(r.months));
        $tr.append($('<td>').text(fmt(r.emi)));
        $tr.append($('<td>').text(r.servedBy));
        $body.append($tr);
      });
    }).fail(function () {
      $('#historyBody').html('<tr><td colspan="6" class="text-danger">Could not load history.</td></tr>');
    });
  }

  $('#emiForm').on('submit', function (e) {
    e.preventDefault();               // no postback
    $('#formError').addClass('d-none');
    if (!validate()) return;

    $('#calcBtn').prop('disabled', true);
    $.ajax({
      url: '/api/emi',
      method: 'POST',
      contentType: 'application/json',
      data: JSON.stringify({ P: $('#P').val(), rate: $('#rate').val(), n: $('#n').val() }),
    }).done(function (d) {
      $('#rEmi').text(fmt(d.emi));
      $('#rTotal').text(fmt(d.totalPayment));
      $('#rInterest').text(fmt(d.totalInterest));
      $('#rPod').text(d.servedBy.pod);
      $('#rIp').text(d.servedBy.ip);
      $('#resultEmpty').addClass('d-none');
      $('#resultBody').removeClass('d-none');
      loadHistory();
    }).fail(function (xhr) {
      const msg = (xhr.responseJSON && xhr.responseJSON.error) || 'Request failed. Try again.';
      $('#formError').text(msg).removeClass('d-none');
    }).always(function () {
      $('#calcBtn').prop('disabled', false);
    });
  });

  $('#emiForm input').on('input', function () { $(this).removeClass('is-invalid'); });
  loadHistory();
});

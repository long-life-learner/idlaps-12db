function exportToExcel(tableId) {
  let cp = prompt("Masukkan nomor pos checkpoint !(1/2/3)");
  let cpNum = Number(cp);
  if (
    cp == null ||
    cp == "" ||
    isNumeric(cpNum) ||
    cp.length > 1 ||
    (cpNum != 1 && cpNum != 2 && cpNum != 3)
  ) {
    alert("Nomor Pos salah");
    return;
  }

  let tableData = document.getElementById(tableId).outerHTML;
  tableData = tableData.replace(/<A[^>]*>|<\/A>/g, ""); //remove if u want links in your table
  tableData = tableData.replace(/<input[^>]*>|<\/input>/gi, ""); //remove input params

  let a = document.createElement("a");
  a.href = `data:application/vnd.ms-excel, ${encodeURIComponent(tableData)}`;
  a.download = "POS" + cp + "-" + getRandomNumbers() + ".xls";
  a.click();
}
function getRandomNumbers() {
  let dateObj = new Date();
  let dateTime = `${dateObj.getHours()}${dateObj.getMinutes()}${dateObj.getSeconds()}`;

  return `${dateTime}${Math.floor(Math.random().toFixed(2) * 100)}`;
}
function isNumeric(str) {
  if (typeof str != "string") return false; // we only process strings!
  return (
    !isNaN(str) && // use type coercion to parse the _entirety_ of the string (`parseFloat` alone does not do this)...
    !isNaN(parseFloat(str))
  ); // ...and ensure strings of whitespace fail
}

export default function formatINR(value: number) {
    const formatter = new Intl.NumberFormat('en-IN', {
        style: 'currency',
        currency: 'INR',
        minimumFractionDigits: 0,
        maximumFractionDigits: 2,
        notation: 'compact',
        currencyDisplay: 'code',
    });
  
    return formatter.format(value).replace("INR", "").trim();
  }
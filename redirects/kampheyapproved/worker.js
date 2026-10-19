// Retired brand: send every kampheyapproved.com request to kamphey.com.
export default {
  fetch() {
    return Response.redirect("https://kamphey.com/", 301);
  },
};

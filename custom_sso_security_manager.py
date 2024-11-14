import logging
import hashlib
from superset.security import SupersetSecurityManager


class CustomSsoSecurityManager(SupersetSecurityManager):

    def oauth_user_info(self, provider, response=None):
        logging.debug("OAuth2 provider: {0}.".format(provider))

        if provider == 'google':
            # Fetch user info from Google's /userinfo endpoint
            me = self.appbuilder.sm.oauth_remotes[provider].get('userinfo')
            data = me.json()
            logging.debug("user_data: {0}".format(data))

            # Retrieve email from Google's response
            email = data.get('email')
            if not email:
                logging.error("No email provided by Google OAuth response.")
                return None

            # Check if a user with this email already exists in the database
            existing_user = self.appbuilder.sm.find_user(email=email)

            if existing_user:
                # Use the existing username if the user already exists
                username = existing_user.username
            else:
                # Generate a unique, reproducible username based on hashed email
                email_hash = hashlib.sha256(email.encode('utf-8')).hexdigest()
                username = f"google_{email_hash[:35]}"  # First 40 characters of hash for brevity

            # Return the user information dictionary, preserving existing usernames
            return {
                'name': data.get('name', ''),
                'email': email,
                'id': data.get('id'),  # Google’s unique user ID
                'username': username,  # Existing or hashed username
                'first_name': data.get('given_name', ''),
                'last_name': data.get('family_name', ''),
            }

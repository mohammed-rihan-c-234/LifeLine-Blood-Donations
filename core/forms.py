from django import forms
from django.contrib.auth.forms import AuthenticationForm

from .models import BloodInventory, User


class LoginForm(AuthenticationForm):
    # Styling handled by global CSS in base.html
    username = forms.CharField(
        widget=forms.TextInput(attrs={'placeholder': 'Enter your username', 'class': 'form-control', 'autocomplete': 'username'}),
        required=True,
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Enter your password', 'autocomplete': 'current-password', 'class': 'form-control'}),
        required=True,
    )


class SignUpForm(forms.ModelForm):
    first_name = forms.CharField(
        label="Name",
        widget=forms.TextInput(attrs={'placeholder': 'Full Name or Hospital Name', 'class': 'form-control', 'autocomplete': 'name'}),
        required=True,
    )

    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'placeholder': 'Choose a unique username',
            'pattern': '[A-Za-z0-9]+',
            'title': 'Use only letters and numbers',
            'autocomplete': 'username',
            'class': 'form-control',
        }),
        required=True,
    )

    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'placeholder': 'Enter your email address',
            'autocomplete': 'email',
            'class': 'form-control',
        }),
        required=True,
    )

    role = forms.ChoiceField(
        choices=(
            ('', 'Select Role'),
            ('user', 'User'),
            ('donor', 'Donor'),
            ('hospital', 'Hospital'),
        ),
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=True,
    )

    blood_group = forms.ChoiceField(
        choices=(('', 'Select Blood Group'),) + User.BLOOD_GROUP_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=False,
    )

    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Enter a password',
            'autocomplete': 'new-password',
            'class': 'form-control',
        }),
        required=True,
    )

    class Meta:
        model = User
        fields = ('first_name', 'username', 'email', 'role', 'blood_group', 'password')

    def clean_username(self):
        username = (self.cleaned_data.get('username') or '').strip()
        if not username:
            return username
        if not username.isalnum():
            raise forms.ValidationError("Username must contain only letters and numbers.")
        qs = User.objects.filter(username__iexact=username)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("This username is already taken.")
        return username

    def clean_email(self):
        email = (self.cleaned_data.get('email') or '').strip()
        if not email:
            raise forms.ValidationError("Email is required.")
        qs = User.objects.filter(email__iexact=email)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if user.role == 'donor':
            user.donor_availability = 'available'
        else:
            user.blood_group = None
        if commit:
            user.save()
        return user


class HospitalCreationForm(forms.ModelForm):
    # Admins set the PIN for the new hospital
    password = forms.CharField(
        label="Set 4-Digit Login PIN",
        widget=forms.TextInput(
            attrs={
                'placeholder': '0000',
                'maxlength': '4',
                'pattern': '[0-9]*',
                'inputmode': 'numeric',
                'class': 'form-control',
            }
        ),
    )
    
    address = forms.CharField(widget=forms.TextInput(attrs={'placeholder': 'City, Street Address', 'class': 'form-control'}))

    class Meta:
        model = User
        # Re-using 'first_name' to store the Hospital Name for simplicity
        fields = ('username', 'first_name', 'address', 'password')
        widgets = {
            'username': forms.TextInput(attrs={'placeholder': 'hospital_login_id', 'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'placeholder': 'Official Hospital Name', 'class': 'form-control'}),
        }

    def clean_password(self):
        password = self.cleaned_data.get('password')
        if not password or len(password) != 4 or not password.isdigit():
            raise forms.ValidationError("Hospital PIN must be exactly 4 digits.")
        return password

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = 'hospital'  # Force role
        user.set_password(self.cleaned_data["password"])

        if commit:
            user.save()
            # Auto-create inventory for the new hospital
            BloodInventory.objects.create(hospital=user)
        return user


class InventoryForm(forms.ModelForm):
    class Meta:
        model = BloodInventory
        exclude = ('hospital', 'updated_at')
        widgets = {
            'a_positive': forms.NumberInput(attrs={'min': 0, 'class': 'form-control'}),
            'a_negative': forms.NumberInput(attrs={'min': 0, 'class': 'form-control'}),
            'b_positive': forms.NumberInput(attrs={'min': 0, 'class': 'form-control'}),
            'b_negative': forms.NumberInput(attrs={'min': 0, 'class': 'form-control'}),
            'ab_positive': forms.NumberInput(attrs={'min': 0, 'class': 'form-control'}),
            'ab_negative': forms.NumberInput(attrs={'min': 0, 'class': 'form-control'}),
            'o_positive': forms.NumberInput(attrs={'min': 0, 'class': 'form-control'}),
            'o_negative': forms.NumberInput(attrs={'min': 0, 'class': 'form-control'}),
        }


class HospitalUpdateForm(forms.ModelForm):
    password = forms.CharField(
        label="Reset Password (optional)",
        widget=forms.PasswordInput(attrs={'placeholder': 'Leave blank to keep current', 'class': 'form-control', 'autocomplete': 'new-password'}),
        required=False,
    )

    class Meta:
        model = User
        fields = ('username', 'first_name', 'address', 'latitude', 'longitude')
        labels = {
            'first_name': 'Hospital Name',
        }
        widgets = {
            'username': forms.TextInput(attrs={
                'pattern': '[A-Za-z0-9]+',
                'title': 'Use only letters and numbers',
                'autocomplete': 'username',
                'class': 'form-control',
            }),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.TextInput(attrs={'placeholder': 'City, Street Address', 'class': 'form-control'}),
            'latitude': forms.NumberInput(attrs={'class': 'form-control'}),
            'longitude': forms.NumberInput(attrs={'class': 'form-control'}),
        }

    def clean_username(self):
        username = (self.cleaned_data.get('username') or '').strip()
        if not username:
            raise forms.ValidationError("Username is required.")
        if not username.isalnum():
            raise forms.ValidationError("Username must contain only letters and numbers.")

        qs = User.objects.filter(username=username)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("This username is already taken.")
        return username

    def save(self, commit=True):
        hospital = super().save(commit=False)
        hospital.role = 'hospital'
        password = self.cleaned_data.get('password')
        if password:
            hospital.set_password(password)
        if commit:
            hospital.save()
        return hospital


class DonorProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('first_name', 'email', 'blood_group', 'last_donation_date', 'address')
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'autocomplete': 'name'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'autocomplete': 'email'}),
            'blood_group': forms.Select(attrs={'class': 'form-control'}),
            'last_donation_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'address': forms.TextInput(attrs={'class': 'form-control'}),
        }

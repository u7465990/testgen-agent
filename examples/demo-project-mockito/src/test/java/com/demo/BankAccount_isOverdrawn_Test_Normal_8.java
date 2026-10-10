package com.demo;

import com.demo.BankAccount;
import org.junit.Test;
import static org.junit.Assert.*;

public class BankAccount_isOverdrawn_Test_Normal_8 {


    @Test
    public void testIsOverdrawnWithRepresentativeInputs() {
        BankAccount overdrawnAccount = new BankAccount("Alice", -50.0);
        boolean overdrawnResult = overdrawnAccount.isOverdrawn();
        assertTrue(overdrawnResult);

        BankAccount fundedAccount = new BankAccount("Bob", 100.0);
        boolean fundedResult = fundedAccount.isOverdrawn();
        assertFalse(fundedResult);
    }

}

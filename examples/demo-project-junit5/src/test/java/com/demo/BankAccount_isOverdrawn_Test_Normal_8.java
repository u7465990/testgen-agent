package com.demo;

import com.demo.BankAccount;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.Assertions;

public class BankAccount_isOverdrawn_Test_Normal_8 {


    @Test
    public void testIsOverdrawnWithTypicalValues() {
        BankAccount overdrawnAccount = new BankAccount("Alice", -150.0);
        boolean overdrawnResult = overdrawnAccount.isOverdrawn();
        Assertions.assertTrue(overdrawnResult, "Account with a negative balance should be overdrawn");

        BankAccount fundedAccount = new BankAccount("Bob", 250.0);
        boolean fundedResult = fundedAccount.isOverdrawn();
        Assertions.assertFalse(fundedResult, "Account with a positive balance should not be overdrawn");
    }

}

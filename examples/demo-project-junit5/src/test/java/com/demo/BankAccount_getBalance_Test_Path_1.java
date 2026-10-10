package com.demo;

import com.demo.BankAccount;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.Assertions;

public class BankAccount_getBalance_Test_Path_1 {


    @Test
    void testGetBalance_CoversReturnStatement() {
        // Construct with a non-zero initial balance to ensure the return statement executes
        BankAccount account = new BankAccount("Alice", 250.75);
        double result = account.getBalance();
        Assertions.assertEquals(250.75, result, 0.0);

        // Construct with a zero initial balance (boundary of the returned value)
        BankAccount zeroAccount = new BankAccount("Bob", 0.0);
        double zeroResult = zeroAccount.getBalance();
        Assertions.assertEquals(0.0, zeroResult, 0.0);

        // Construct with a negative initial balance to fully exercise the single return path
        BankAccount negativeAccount = new BankAccount("Carol", -100.5);
        double negativeResult = negativeAccount.getBalance();
        Assertions.assertEquals(-100.5, negativeResult, 0.0);
    }

}
